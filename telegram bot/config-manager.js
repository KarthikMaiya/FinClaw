#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

const PROJECT_ROOT = __dirname;
const DOTENV_PATH = path.join(PROJECT_ROOT, '.env');
const ACTUAL_CONFIG_PATH = path.join(PROJECT_ROOT, 'integrations', 'config.json');

let cachedRuntimeConfig = null;
let dotenvLoaded = false;

function loadDotEnv() {
  if (dotenvLoaded) {
    return;
  }

  dotenv.config({ path: DOTENV_PATH });
  dotenvLoaded = true;
}

function isTruthy(value) {
  return ['1', 'true', 'yes', 'on'].includes(String(value || '').toLowerCase());
}

function readJson(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }

  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    return {};
  }
}

function normalizeProviders(rawValue) {
  const providers = String(rawValue || 'openai')
    .toLowerCase()
    .split(',')
    .map((provider) => provider.trim())
    .filter(Boolean);

  return providers.length > 0 ? providers : ['openai'];
}

function buildRuntimeConfig() {
  loadDotEnv();

  const actualFileConfig = readJson(ACTUAL_CONFIG_PATH);
  const aiProvider = normalizeProviders(process.env.AI_PROVIDER);

  const runtimeConfig = {
    projectRoot: PROJECT_ROOT,
    dotenvPath: DOTENV_PATH,
    actualConfigPath: ACTUAL_CONFIG_PATH,
    telegramBotToken: String(process.env.TELEGRAM_BOT_TOKEN || '').trim(),
    actualServerUrl: String(process.env.ACTUAL_SERVER_URL || '').trim(),
    actualPassword: String(process.env.ACTUAL_PASSWORD || '').trim(),
    actualBudgetId: String(process.env.ACTUAL_BUDGET_ID || actualFileConfig.budgetId || '').trim(),
    actualBudgetName: String(process.env.ACTUAL_BUDGET_NAME || actualFileConfig.budgetName || 'Budget').trim(),
    actualModuleDir: String(process.env.ACTUAL_MODULE_DIR || './node_modules').trim(),
    aiProvider,
    aiProviderRaw: String(process.env.AI_PROVIDER || 'openai').trim(),
    aiApiKey: String(process.env.AI_API_KEY || '').trim(),
    openAiApiKey: String(process.env.OPENAI_API_KEY || '').trim(),
    googleApiKey: String(process.env.GOOGLE_API_KEY || '').trim(),
    configDebug: isTruthy(process.env.CONFIG_DEBUG || process.env.DEBUG_CONFIG),
  };

  runtimeConfig.configuredServices = {
    telegram: !!runtimeConfig.telegramBotToken,
    actualBudget: !!(runtimeConfig.actualServerUrl && runtimeConfig.actualPassword && runtimeConfig.actualBudgetId),
    ai: !!(runtimeConfig.aiApiKey || runtimeConfig.openAiApiKey || runtimeConfig.googleApiKey),
  };

  runtimeConfig.missingRequired = [];
  if (!runtimeConfig.telegramBotToken) {
    runtimeConfig.missingRequired.push('TELEGRAM_BOT_TOKEN');
  }
  if (!runtimeConfig.actualServerUrl) {
    runtimeConfig.missingRequired.push('ACTUAL_SERVER_URL');
  }
  if (!runtimeConfig.actualPassword) {
    runtimeConfig.missingRequired.push('ACTUAL_PASSWORD');
  }
  if (!runtimeConfig.actualBudgetId) {
    runtimeConfig.missingRequired.push('ACTUAL_BUDGET_ID or integrations/config.json budgetId');
  }

  runtimeConfig.missingOptional = [];
  if (runtimeConfig.aiProvider.includes('openai') && !runtimeConfig.aiApiKey && !runtimeConfig.openAiApiKey && !runtimeConfig.googleApiKey) {
    runtimeConfig.missingOptional.push('AI_API_KEY or OPENAI_API_KEY');
  }
  if (runtimeConfig.aiProvider.includes('gemini') && !runtimeConfig.googleApiKey && !runtimeConfig.aiApiKey) {
    runtimeConfig.missingOptional.push('GOOGLE_API_KEY or AI_API_KEY');
  }

  return runtimeConfig;
}

function getRuntimeConfig(options = {}) {
  if (options.refresh) {
    cachedRuntimeConfig = null;
  }

  if (!cachedRuntimeConfig) {
    cachedRuntimeConfig = buildRuntimeConfig();
  }

  return cachedRuntimeConfig;
}

function validateRequiredConfig(options = {}) {
  const runtimeConfig = getRuntimeConfig(options);
  const required = [];

  if (options.requireTelegram && !runtimeConfig.telegramBotToken) {
    required.push('TELEGRAM_BOT_TOKEN');
  }
  if (options.requireActual && !runtimeConfig.actualServerUrl) {
    required.push('ACTUAL_SERVER_URL');
  }
  if (options.requireActual && !runtimeConfig.actualPassword) {
    required.push('ACTUAL_PASSWORD');
  }
  if (options.requireBudgetId && !runtimeConfig.actualBudgetId) {
    required.push('ACTUAL_BUDGET_ID or integrations/config.json budgetId');
  }

  if (required.length > 0) {
    const lines = [
      `Missing required environment configuration: ${required.join(', ')}`,
      'Copy .env.example to .env and fill in the required values.',
    ];
    throw new Error(lines.join(' '));
  }

  return runtimeConfig;
}

function getActualBudgetConfig(options = {}) {
  const runtimeConfig = validateRequiredConfig({ ...options, requireActual: true, requireBudgetId: true });
  return {
    serverUrl: runtimeConfig.actualServerUrl,
    password: runtimeConfig.actualPassword,
    budgetId: runtimeConfig.actualBudgetId,
    budgetName: runtimeConfig.actualBudgetName,
    moduleDir: runtimeConfig.actualModuleDir,
    configPath: runtimeConfig.actualConfigPath,
  };
}

function getTelegramConfig(options = {}) {
  const runtimeConfig = validateRequiredConfig({ ...options, requireTelegram: true });
  return {
    botToken: runtimeConfig.telegramBotToken,
  };
}

function getAiConfig() {
  const runtimeConfig = getRuntimeConfig();
  return {
    providers: runtimeConfig.aiProvider,
    providerRaw: runtimeConfig.aiProviderRaw,
    aiApiKey: runtimeConfig.aiApiKey,
    openAiApiKey: runtimeConfig.openAiApiKey,
    googleApiKey: runtimeConfig.googleApiKey,
    configDebug: runtimeConfig.configDebug,
    missingOptional: runtimeConfig.missingOptional,
  };
}

function getDebugSummary() {
  const runtimeConfig = getRuntimeConfig();
  return {
    loadedProvider: runtimeConfig.aiProvider.join(','),
    configuredServices: runtimeConfig.configuredServices,
    missingOptionalConfigs: runtimeConfig.missingOptional,
    missingRequiredConfigs: runtimeConfig.missingRequired,
  };
}

function printDebugSummary(label = 'config-manager') {
  const summary = getDebugSummary();
  const serviceSummary = Object.entries(summary.configuredServices)
    .map(([name, enabled]) => `${name}=${enabled ? 'yes' : 'no'}`)
    .join(', ');

  console.log(`[${label}] loaded provider(s): ${summary.loadedProvider || 'none'}`);
  console.log(`[${label}] configured services: ${serviceSummary}`);
  if (summary.missingOptionalConfigs.length > 0) {
    console.log(`[${label}] missing optional configs: ${summary.missingOptionalConfigs.join(', ')}`);
  }
  if (summary.missingRequiredConfigs.length > 0) {
    console.log(`[${label}] missing required configs: ${summary.missingRequiredConfigs.join(', ')}`);
  }
}

module.exports = {
  loadDotEnv,
  getRuntimeConfig,
  validateRequiredConfig,
  getActualBudgetConfig,
  getTelegramConfig,
  getAiConfig,
  getDebugSummary,
  printDebugSummary,
  readJson,
  normalizeProviders,
};

if (require.main === module) {
  const runtimeConfig = getRuntimeConfig();
  printDebugSummary('config-manager');
  if (process.argv.includes('--validate')) {
    validateRequiredConfig({ requireTelegram: false, requireActual: false, requireBudgetId: false });
  }
  if (runtimeConfig.configDebug) {
    console.log('[config-manager] debug mode enabled');
  }
}