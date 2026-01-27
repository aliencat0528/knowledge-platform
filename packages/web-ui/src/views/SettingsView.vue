<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

interface SystemStatus {
  articles_count: number
  embedded_count: number
  conversations_count: number
  database_size: string
}

interface ProviderConfig {
  llm_provider: string
  llm_model: string
  embedding_provider: string
  embedding_model: string
}

const status = ref<SystemStatus | null>(null)
const providerConfig = ref<ProviderConfig>({
  llm_provider: 'openai',
  llm_model: 'gpt-4o-mini',
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
})
const loading = ref(false)
const error = ref<string | null>(null)
const saveSuccess = ref(false)

const llmProviders = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama (本地)' },
]

const embeddingProviders = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'ollama', label: 'Ollama (本地)' },
]

const llmModels: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-opus-4-5-20251101', 'claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022'],
  ollama: ['llama3.2', 'llama3.1', 'mistral', 'codellama'],
}

const embeddingModels: Record<string, string[]> = {
  openai: ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
  ollama: ['nomic-embed-text', 'mxbai-embed-large', 'all-minilm'],
}

async function fetchStatus() {
  try {
    const response = await api.get('/stats')
    status.value = response.data
  } catch (e) {
    console.error('Failed to fetch status:', e)
  }
}

async function fetchProviderConfig() {
  try {
    const response = await api.get('/providers/current')
    if (response.data) {
      providerConfig.value = {
        llm_provider: response.data.llm?.provider || 'openai',
        llm_model: response.data.llm?.model || 'gpt-4o-mini',
        embedding_provider: response.data.embedding?.provider || 'openai',
        embedding_model: response.data.embedding?.model || 'text-embedding-3-small',
      }
    }
  } catch (e) {
    // API might not exist yet, use defaults
    console.warn('Provider config API not available, using defaults')
  }
}

async function saveConfig() {
  loading.value = true
  error.value = null
  saveSuccess.value = false

  try {
    await api.put('/providers/current', providerConfig.value)
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 3000)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '儲存失敗'
  } finally {
    loading.value = false
  }
}

async function testProvider(type: 'llm' | 'embedding') {
  loading.value = true
  error.value = null

  try {
    const response = await api.post('/providers/test', {
      provider_type: type,
      provider: type === 'llm' ? providerConfig.value.llm_provider : providerConfig.value.embedding_provider,
      model: type === 'llm' ? providerConfig.value.llm_model : providerConfig.value.embedding_model,
    })
    alert(`連線成功！延遲：${response.data.latency_ms}ms`)
  } catch (e) {
    error.value = `測試失敗：${e instanceof Error ? e.message : '未知錯誤'}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  fetchProviderConfig()
})
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">設定</h1>

    <!-- System Status -->
    <section class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">系統狀態</h2>

      <div v-if="status" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div class="text-2xl font-bold text-primary-600">{{ status.articles_count }}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">文章數量</div>
        </div>
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div class="text-2xl font-bold text-green-600">{{ status.embedded_count }}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">已向量化</div>
        </div>
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div class="text-2xl font-bold text-purple-600">{{ status.conversations_count }}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">對話數量</div>
        </div>
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div class="text-2xl font-bold text-gray-600 dark:text-gray-300">{{ status.database_size }}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">資料庫大小</div>
        </div>
      </div>

      <div v-else class="text-center py-8 text-gray-500">
        載入中...
      </div>
    </section>

    <!-- Provider Settings -->
    <section class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">AI Provider 設定</h2>

      <div v-if="error" class="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
        {{ error }}
      </div>

      <div v-if="saveSuccess" class="mb-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded-lg">
        設定已儲存
      </div>

      <!-- LLM Provider -->
      <div class="mb-6">
        <h3 class="font-medium text-gray-700 dark:text-gray-300 mb-3">LLM Provider</h3>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Provider</label>
            <select
              v-model="providerConfig.llm_provider"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option v-for="p in llmProviders" :key="p.value" :value="p.value">
                {{ p.label }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Model</label>
            <select
              v-model="providerConfig.llm_model"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option v-for="m in llmModels[providerConfig.llm_provider]" :key="m" :value="m">
                {{ m }}
              </option>
            </select>
          </div>
        </div>
        <button
          @click="testProvider('llm')"
          :disabled="loading"
          class="mt-2 text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
        >
          測試連線
        </button>
      </div>

      <!-- Embedding Provider -->
      <div class="mb-6">
        <h3 class="font-medium text-gray-700 dark:text-gray-300 mb-3">Embedding Provider</h3>
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Provider</label>
            <select
              v-model="providerConfig.embedding_provider"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option v-for="p in embeddingProviders" :key="p.value" :value="p.value">
                {{ p.label }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Model</label>
            <select
              v-model="providerConfig.embedding_model"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option v-for="m in embeddingModels[providerConfig.embedding_provider]" :key="m" :value="m">
                {{ m }}
              </option>
            </select>
          </div>
        </div>
        <button
          @click="testProvider('embedding')"
          :disabled="loading"
          class="mt-2 text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
        >
          測試連線
        </button>
      </div>

      <!-- Save Button -->
      <button
        @click="saveConfig"
        :disabled="loading"
        class="w-full py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
      >
        {{ loading ? '儲存中...' : '儲存設定' }}
      </button>

      <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
        注意：API Key 需在伺服器端的 .env 檔案中設定
      </p>
    </section>

    <!-- About -->
    <section class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">關於</h2>
      <div class="text-sm text-gray-600 dark:text-gray-400 space-y-2">
        <p><strong>Knowledge Platform</strong> - 個人知識管理平台</p>
        <p>整合多種來源的技術文章與筆記，支援語意搜尋和 AI 對話。</p>
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700 mt-4">
          <p>技術棧：FastAPI + SQLite + ChromaDB + Vue 3</p>
        </div>
      </div>
    </section>
  </div>
</template>
