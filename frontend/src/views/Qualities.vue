<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listQualities, createQuality, deleteQuality } from '@/api/qualities'
import type { Quality } from '@/types'
import NavBar from '@/components/NavBar.vue'

const qualities = ref<Quality[]>([])
const showForm = ref(false)
const newName = ref('')
const newDesc = ref('')

async function load() {
  qualities.value = await listQualities()
}

async function handleCreate() {
  if (!newName.value.trim()) return
  await createQuality({ name: newName.value.trim(), description: newDesc.value.trim() })
  newName.value = ''
  newDesc.value = ''
  showForm.value = false
  await load()
}

async function handleDelete(id: number) {
  await deleteQuality(id)
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page-content px-4 pt-6">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">品质目标</h1>
      <button
        @click="showForm = !showForm"
        class="px-3 py-1.5 text-sm bg-amber-400 text-white rounded-lg hover:bg-amber-500 transition-colors"
      >+ 新增</button>
    </div>

    <!-- Create Form -->
    <div v-if="showForm" class="bg-amber-50 rounded-xl p-4 mb-4 space-y-3">
      <input
        v-model="newName"
        placeholder="品质名称，如：自律"
        class="w-full px-3 py-2 rounded-lg border border-amber-200 text-sm outline-none focus:border-amber-400"
      />
      <input
        v-model="newDesc"
        placeholder="描述，如：坚持完成每日计划"
        class="w-full px-3 py-2 rounded-lg border border-amber-200 text-sm outline-none focus:border-amber-400"
      />
      <div class="flex gap-2">
        <button @click="handleCreate" class="flex-1 py-2 bg-amber-400 text-white rounded-lg text-sm hover:bg-amber-500">创建</button>
        <button @click="showForm = false" class="px-4 py-2 bg-gray-100 text-gray-500 rounded-lg text-sm hover:bg-gray-200">取消</button>
      </div>
    </div>

    <!-- Quality List -->
    <div class="space-y-3">
      <div
        v-for="q in qualities"
        :key="q.id"
        class="bg-white rounded-xl border border-gray-100 p-4 shadow-sm"
      >
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-medium">{{ q.name }}</h3>
            <p class="text-xs text-gray-400 mt-0.5">{{ q.description || '暂无描述' }}</p>
            <p class="text-xs text-gray-300 mt-1">创建于 {{ q.created_at.slice(0, 10) }}</p>
          </div>
          <button @click="handleDelete(q.id)" class="text-xs text-gray-300 hover:text-red-400 transition-colors">删除</button>
        </div>
      </div>

      <div v-if="qualities.length === 0" class="text-center text-gray-300 text-sm py-12">
        还没有品质目标，点击「+ 新增」创建第一个吧
      </div>
    </div>

    <NavBar />
  </div>
</template>
