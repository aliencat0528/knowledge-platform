<script setup lang="ts">
import { onMounted } from 'vue'
import { useArticlesStore } from '../stores/articles'
import ArticleList from '../components/ArticleList.vue'

const store = useArticlesStore()

onMounted(() => {
  store.fetchArticles()
})

async function handleDelete(id: number) {
  if (confirm('確定要刪除這篇文章嗎？')) {
    try {
      await store.deleteArticle(id)
    } catch (e) {
      alert('刪除失敗')
    }
  }
}
</script>

<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">文章列表</h1>
      <p class="text-gray-600 dark:text-gray-400">共 {{ store.total }} 篇文章</p>
    </div>

    <div v-if="store.loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <div v-else-if="store.error" class="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
      <p class="text-red-600 dark:text-red-400">{{ store.error }}</p>
    </div>

    <ArticleList v-else :articles="store.articles" @delete="handleDelete" />

    <div v-if="store.hasMore" class="mt-6 text-center">
      <button
        @click="store.fetchArticles(store.currentPage + 1)"
        class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
      >
        載入更多
      </button>
    </div>
  </div>
</template>
