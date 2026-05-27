<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getTodosByDate, checkIn, skipTodo } from '@/api/todos'
import type { TodoItem } from '@/types'
import { formatLocalDate } from '@/utils/date'
import NavBar from '@/components/NavBar.vue'
import TodoItemVue from '@/components/TodoItem.vue'

const date = ref(formatLocalDate())
const todos = ref<TodoItem[]>([])
const todayScore = ref(0)

async function load() {
  const res = await getTodosByDate(date.value)
  todos.value = res.items
}

function groupByCategory(): Record<string, TodoItem[]> {
  const cats = ['学习', '运动', '工作', '生活', '阅读', '冥想']
  const result: Record<string, TodoItem[]> = {}
  for (const cat of cats) {
    const items = todos.value.filter(t => t.category === cat)
    if (items.length) result[cat] = items
  }
  const rest = todos.value.filter(t => !cats.includes(t.category))
  if (rest.length) result['其他'] = rest
  return result
}

const groupedTodos = ref<Record<string, TodoItem[]>>({})

async function handleDateChange() {
  await load()
  groupedTodos.value = groupByCategory()
  todayScore.value = 0
}

async function handleCheckIn(id: number) {
  const res = await checkIn(id)
  todayScore.value += res.score_earned
  await load()
  groupedTodos.value = groupByCategory()
}

async function handleSkip(id: number) {
  await skipTodo(id)
  await load()
  groupedTodos.value = groupByCategory()
}

onMounted(async () => {
  await load()
  groupedTodos.value = groupByCategory()
})
</script>

<template>
  <div class="page-content px-4 pt-6">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">打卡</h1>
      <input
        type="date"
        v-model="date"
        @change="handleDateChange"
        class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm outline-none"
      />
    </div>

    <div v-if="todayScore > 0" class="bg-amber-50 rounded-xl p-3 mb-4 text-center">
      <span class="text-sm text-amber-600">本次已获得 <strong>{{ todayScore }}</strong> 积分 </span>
    </div>

    <div class="space-y-4">
      <div v-for="(items, cat) in groupedTodos" :key="cat">
        <h2 class="text-sm font-medium text-gray-400 mb-2">{{ cat }}</h2>
        <div class="space-y-1.5">
          <TodoItemVue
            v-for="t in items"
            :key="t.id"
            :todo="t"
            @checkin="handleCheckIn"
            @skip="handleSkip"
          />
        </div>
      </div>
    </div>

    <div v-if="todos.length === 0" class="text-center text-gray-300 text-sm py-12">
      今天还没有任务
    </div>

    <NavBar />
  </div>
</template>
