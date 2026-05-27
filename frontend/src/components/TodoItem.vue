<script setup lang="ts">
import { ref } from 'vue'
import type { TodoItem } from '@/types'

const props = defineProps<{ todo: TodoItem }>()
const showDetail = ref(false)
const emit = defineEmits<{
  checkin: [id: number]
  skip: [id: number]
}>()

const tagColors: Record<string, string> = {
  '学习': 'bg-blue-50 text-blue-600',
  '运动': 'bg-green-50 text-green-600',
  '工作': 'bg-purple-50 text-purple-600',
  '生活': 'bg-orange-50 text-orange-600',
  '阅读': 'bg-indigo-50 text-indigo-600',
  '冥想': 'bg-teal-50 text-teal-600',
}
</script>

<template>
  <div
    class="flex items-center gap-3 p-3 rounded-lg border border-gray-100 bg-white transition-colors"
    :class="{
      'opacity-60': todo.status === 'done',
      'opacity-40 line-through': todo.status === 'skipped',
    }"
  >
    <button
      v-if="todo.status === 'pending'"
      @click="emit('checkin', todo.id)"
      class="w-5 h-5 rounded-full border-2 border-gray-300 flex-shrink-0 hover:border-green-400 transition-colors"
    ></button>
    <svg
      v-else-if="todo.status === 'done'"
      class="w-5 h-5 text-green-500 flex-shrink-0"
      fill="none" stroke="currentColor" viewBox="0 0 24 24"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <span
      v-else
      class="w-5 h-5 flex-shrink-0 text-gray-300 text-xs flex items-center justify-center"
    >--</span>

    <div class="flex-1 min-w-0">
      <p class="text-sm truncate">{{ todo.content }}</p>
      <div class="flex gap-2 mt-0.5">
        <span class="text-xs px-1.5 py-0.5 rounded" :class="tagColors[todo.category] || 'bg-gray-50 text-gray-500'">
          {{ todo.category }}
        </span>
        <span class="text-xs text-gray-400">{{ todo.duration_minutes }}分钟</span>
      </div>
    </div>

    <button
      @click="showDetail = true"
      class="text-xs text-gray-300 hover:text-amber-500 transition-colors flex-shrink-0"
    >详情</button>
    <button
      v-if="todo.status === 'pending'"
      @click="emit('skip', todo.id)"
      class="text-xs text-gray-300 hover:text-gray-500 transition-colors flex-shrink-0"
    >跳过</button>
  </div>

  <!-- Detail Modal -->
  <Teleport to="body">
    <div
      v-if="showDetail"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="showDetail = false"
    >
      <div class="bg-white rounded-xl shadow-xl w-[340px] max-h-[80vh] overflow-y-auto mx-4">
        <div class="p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold text-gray-800">任务详情</h3>
            <button
              @click="showDetail = false"
              class="w-6 h-6 flex items-center justify-center rounded-full text-gray-300 hover:text-gray-500 hover:bg-gray-100 transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p class="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap break-words">{{ todo.content }}</p>

          <div class="flex gap-2 mt-3">
            <span class="text-xs px-2 py-0.5 rounded" :class="tagColors[todo.category] || 'bg-gray-50 text-gray-500'">
              {{ todo.category }}
            </span>
            <span class="text-xs px-2 py-0.5 rounded bg-gray-50 text-gray-500">
              {{ todo.status === 'done' ? '已完成' : todo.status === 'skipped' ? '已跳过' : '待完成' }}
            </span>
          </div>

          <div class="mt-4 space-y-1.5 text-xs text-gray-500">
            <div class="flex justify-between">
              <span>预计时长</span>
              <span>{{ todo.duration_minutes }} 分钟</span>
            </div>
            <div v-if="todo.status === 'done'" class="flex justify-between">
              <span>实际时长</span>
              <span>{{ todo.actual_duration }} 分钟</span>
            </div>
            <div class="flex justify-between">
              <span>创建时间</span>
              <span>{{ todo.created_at?.substring(0, 16) }}</span>
            </div>
            <div v-if="todo.completed_at" class="flex justify-between">
              <span>完成时间</span>
              <span>{{ todo.completed_at?.substring(0, 16) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
