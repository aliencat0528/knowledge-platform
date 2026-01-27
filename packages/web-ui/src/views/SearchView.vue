<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'
import type { SearchResult } from '../types/article'

const query = ref('')
const results = ref<SearchResult[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchMode = ref<'keyword' | 'semantic'>('keyword')

async function search() {
  if (!query.value.trim()) return

  loading.value = true
  error.value = null
  results.value = []

  try {
    if (searchMode.value === 'keyword') {
      const response = await api.get('/search', {
        params: { q: query.value, limit: 20 },
      })
      results.value = response.data.results
    } else {
      const response = await api.post('/search/semantic', {
        query: query.value,
        limit: 20,
      })
      results.value = response.data.results
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="p-6">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">搜尋</h1>

    <div class="max-w-2xl">
      <div class="flex gap-2 mb-4">
        <input
          v-model="query"
          type="text"
          placeholder="輸入搜尋關鍵字..."
          class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          @keyup.enter="search"
        />
        <button
          @click="search"
          :disabled="loading"
          class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          搜尋
        </button>
      </div>

      <div class="flex gap-4 mb-6">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="searchMode"
            type="radio"
            value="keyword"
            class="text-primary-600"
          />
          <span class="text-gray-700 dark:text-gray-300">關鍵字搜尋</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="searchMode"
            type="radio"
            value="semantic"
            class="text-primary-600"
          />
          <span class="text-gray-700 dark:text-gray-300">語意搜尋</span>
        </label>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
      <p class="text-red-600 dark:text-red-400">{{ error }}</p>
    </div>

    <div v-else-if="results.length > 0" class="space-y-4">
      <div
        v-for="result in results"
        :key="result.article.id"
        class="p-4 bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow"
      >
        <h3 class="font-semibold text-gray-900 dark:text-white">
          {{ result.article.title }}
        </h3>
        <p v-if="result.snippet" class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {{ result.snippet }}
        </p>
        <div class="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span>相似度: {{ (result.score * 100).toFixed(1) }}%</span>
          <span>{{ result.article.source_type }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="query" class="text-center py-12 text-gray-500">
      沒有找到相關結果
    </div>
  </div>
</template>
