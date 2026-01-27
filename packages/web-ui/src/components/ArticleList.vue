<script setup lang="ts">
import type { Article } from '../types/article'

defineProps<{
  articles: Article[]
}>()

const emit = defineEmits<{
  delete: [id: number]
}>()

function getSourceTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    notion: 'Notion',
    web: '網頁',
    docs: '文件',
    chat: '對話',
  }
  return labels[type] || type
}

function getSourceTypeColor(type: string): string {
  const colors: Record<string, string> = {
    notion: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    web: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    docs: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    chat: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  }
  return colors[type] || 'bg-gray-100 text-gray-800'
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function truncateContent(content: string, maxLength: number = 150): string {
  if (content.length <= maxLength) return content
  return content.slice(0, maxLength) + '...'
}
</script>

<template>
  <div class="space-y-4">
    <div
      v-for="article in articles"
      :key="article.id"
      class="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow p-4"
    >
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1 min-w-0">
          <!-- Title -->
          <h3 class="font-semibold text-gray-900 dark:text-white truncate">
            <a
              v-if="article.url"
              :href="article.url"
              target="_blank"
              class="hover:text-primary-600 dark:hover:text-primary-400"
            >
              {{ article.title }}
            </a>
            <span v-else>{{ article.title }}</span>
          </h3>

          <!-- Content Preview -->
          <p class="mt-2 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
            {{ truncateContent(article.content) }}
          </p>

          <!-- Meta -->
          <div class="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <!-- Source Type Badge -->
            <span
              :class="[
                'px-2 py-0.5 rounded-full font-medium',
                getSourceTypeColor(article.source_type)
              ]"
            >
              {{ getSourceTypeLabel(article.source_type) }}
            </span>

            <!-- Tags -->
            <span
              v-for="tag in article.tags?.slice(0, 3)"
              :key="tag"
              class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full"
            >
              {{ tag }}
            </span>

            <!-- Date -->
            <span class="text-gray-500 dark:text-gray-500 ml-auto">
              {{ formatDate(article.created_at) }}
            </span>

            <!-- Embedded Status -->
            <span
              v-if="article.is_embedded"
              class="text-green-600 dark:text-green-400"
              title="已向量化"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1">
          <a
            v-if="article.url"
            :href="article.url"
            target="_blank"
            class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            title="開啟連結"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
          <button
            @click="emit('delete', article.id)"
            class="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            title="刪除"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="articles.length === 0"
      class="text-center py-12 text-gray-500 dark:text-gray-400"
    >
      <svg class="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p>目前沒有文章</p>
      <p class="text-sm mt-1">使用擴充套件或匯入功能新增文章</p>
    </div>
  </div>
</template>
