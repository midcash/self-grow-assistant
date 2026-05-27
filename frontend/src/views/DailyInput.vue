<script setup lang="ts">
import { ref } from 'vue'
import { parseTodos, batchCreate } from '@/api/todos'
import type { ParsedTodo } from '@/types'
import { formatLocalDate } from '@/utils/date'
import NavBar from '@/components/NavBar.vue'

const text = ref('')
const date = ref(formatLocalDate())
const parsed = ref<ParsedTodo[]>([])
const loading = ref(false)
const saved = ref(false)

async function handleParse() {
  if (!text.value.trim()) return
  loading.value = true
  saved.value = false
  const res = await parseTodos(text.value, date.value)
  parsed.value = res.parsed
  loading.value = false
}

async function handleSave() {
  if (!parsed.value.length) return
  await batchCreate(date.value, parsed.value)
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
  parsed.value = []
  text.value = ''
}

function removeTodo(idx: number) {
  parsed.value.splice(idx, 1)
}

const categories = ['学习', '运动', '工作', '生活', '阅读', '冥想', '其他']
</script>

<template>
  <div class="page-content px-4 pt-6">
    <h1 class="text-xl font-bold mb-4">日程录入</h1>

    <div class="mb-3">
      <input
        type="date"
        v-model="date"
        class="px-3 py-2 rounded-lg border border-gray-200 text-sm outline-none focus:border-amber-400"
      />
    </div>

    <textarea
      v-model="text"
      placeholder="上午读2小时《原则》
下午跑步40分钟
晚上练习Python编程1小时"
      rows="6"
      class="w-full px-3 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-amber-400 resize-none"
    ></textarea>

    <div class="flex gap-2 mt-3">
      <button
        @click="handleParse"
        :disabled="!text.trim() || loading"
        class="flex-1 py-2 bg-amber-400 text-white rounded-lg text-sm hover:bg-amber-500 disabled:opacity-40 transition-all"
      >{{ loading ? '解析中...' : '智能解析' }}</button>
      <button
        v-if="parsed.length"
        @click="handleSave"
        class="flex-1 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600 transition-colors"
      >{{ saved ? '已保存' : '保存到 ' + date }}</button>
    </div>

    <div v-if="parsed.length" class="mt-4 space-y-2">
      <h2 class="text-sm font-medium text-gray-500">解析结果（可编辑）</h2>
      <div
        v-for="(item, idx) in parsed"
        :key="idx"
        class="flex items-center gap-2 p-3 rounded-lg border border-gray-100 bg-white"
      >
        <div class="flex-1 min-w-0">
          <input
            v-model="item.content"
            class="w-full text-sm outline-none border-b border-transparent focus:border-gray-200 py-0.5"
          />
        </div>
        <select
          v-model="item.category"
          class="text-xs px-2 py-1 rounded border border-gray-200 outline-none"
        >
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <input
          type="number"
          v-model="item.duration_minutes"
          class="w-16 text-xs px-2 py-1 rounded border border-gray-200 outline-none text-right"
          min="0"
        />
        <span class="text-xs text-gray-400">分钟</span>
        <button @click="removeTodo(idx)" class="text-gray-300 hover:text-red-400 text-xs">x</button>
      </div>
    </div>

    <NavBar />
  </div>
</template>
