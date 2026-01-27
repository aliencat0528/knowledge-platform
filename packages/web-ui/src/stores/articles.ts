import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Article, ArticleListResponse } from '../types/article'
import { api } from '../api/client'

export const useArticlesStore = defineStore('articles', () => {
  const articles = ref<Article[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const pageSize = ref(20)

  const hasMore = computed(() => articles.value.length < total.value)

  async function fetchArticles(page = 1, limit = 20) {
    loading.value = true
    error.value = null
    try {
      const offset = (page - 1) * limit
      const response = await api.get<ArticleListResponse>('/articles', {
        params: { limit, offset },
      })
      articles.value = response.data.articles
      total.value = response.data.total
      currentPage.value = page
      pageSize.value = limit
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch articles'
    } finally {
      loading.value = false
    }
  }

  async function deleteArticle(id: number) {
    try {
      await api.delete(`/articles/${id}`)
      articles.value = articles.value.filter((a) => a.id !== id)
      total.value--
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete article'
      throw e
    }
  }

  return {
    articles,
    total,
    loading,
    error,
    currentPage,
    pageSize,
    hasMore,
    fetchArticles,
    deleteArticle,
  }
})
