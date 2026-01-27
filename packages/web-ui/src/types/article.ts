export type SourceType = 'notion' | 'web' | 'docs' | 'chat'

export interface Article {
  id: number
  source_type: SourceType
  source_id: string
  title: string
  content: string
  url?: string
  tags?: string[]
  parent_id?: number
  is_embedded: boolean
  notion_page_id?: string
  notion_synced_at?: string
  created_at: string
  updated_at: string
}

export interface ArticleListResponse {
  articles: Article[]
  total: number
  limit: number
  offset: number
}

export interface ArticleCreate {
  source_type: SourceType
  source_id: string
  title: string
  content: string
  url?: string
  tags?: string[]
  parent_id?: number
}

export interface SearchResult {
  article: Article
  score: number
  snippet?: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
}
