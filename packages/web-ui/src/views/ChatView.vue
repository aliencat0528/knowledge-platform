<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { api } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    id: number
    title: string
    url?: string
  }>
}

const messages = ref<Message[]>([])
const input = ref('')
const loading = ref(false)
const conversationId = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)

async function sendMessage() {
  if (!input.value.trim() || loading.value) return

  const userMessage = input.value
  input.value = ''

  messages.value.push({
    role: 'user',
    content: userMessage,
  })

  await scrollToBottom()

  loading.value = true

  try {
    const response = await api.post('/chat', {
      message: userMessage,
      conversation_id: conversationId.value,
    })

    conversationId.value = response.data.data.conversation_id

    messages.value.push({
      role: 'assistant',
      content: response.data.data.answer,
      sources: response.data.data.sources,
    })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，發生錯誤。請稍後再試。',
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function newChat() {
  messages.value = []
  conversationId.value = null
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-4rem)]">
    <div class="flex items-center justify-between p-4 border-b dark:border-gray-700">
      <h1 class="text-xl font-bold text-gray-900 dark:text-white">Chat</h1>
      <button
        @click="newChat"
        class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
      >
        新對話
      </button>
    </div>

    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-4"
    >
      <div v-if="messages.length === 0" class="text-center py-12 text-gray-500">
        <p class="text-lg">開始與你的知識庫對話</p>
        <p class="text-sm mt-2">詢問任何關於你收藏文章的問題</p>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="[
          'max-w-3xl',
          message.role === 'user' ? 'ml-auto' : 'mr-auto',
        ]"
      >
        <div
          :class="[
            'p-4 rounded-lg',
            message.role === 'user'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white',
          ]"
        >
          <p class="whitespace-pre-wrap">{{ message.content }}</p>

          <div
            v-if="message.sources?.length"
            class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700"
          >
            <p class="text-xs opacity-75 mb-2">參考來源：</p>
            <div class="space-y-1">
              <a
                v-for="source in message.sources"
                :key="source.id"
                :href="source.url"
                target="_blank"
                class="block text-xs underline hover:opacity-75"
              >
                {{ source.title }}
              </a>
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="flex justify-start">
        <div class="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <div class="flex space-x-2">
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="p-4 border-t dark:border-gray-700">
      <div class="flex gap-2 max-w-3xl mx-auto">
        <input
          v-model="input"
          type="text"
          placeholder="輸入訊息..."
          class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          @keyup.enter="sendMessage"
          :disabled="loading"
        />
        <button
          @click="sendMessage"
          :disabled="loading || !input.trim()"
          class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          發送
        </button>
      </div>
    </div>
  </div>
</template>
