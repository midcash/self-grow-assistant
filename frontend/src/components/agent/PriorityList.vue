<script setup lang="ts">
import { useAgent } from '@/composables/useAgent'
import type { PriorityTask } from '@/api/agent'

const { priorityTasks, fetchPriorityTasks } = useAgent()

defineExpose({ refresh: fetchPriorityTasks })

function getScoreColor(score: number): string {
  if (score > 0.7) return 'text-red-400'
  if (score > 0.4) return 'text-amber-400'
  return 'text-gray-400'
}

function getScoreBg(score: number): string {
  if (score > 0.7) return 'bg-red-500'
  if (score > 0.4) return 'bg-amber-500'
  return 'bg-gray-500'
}

function getUrgencyLabel(task: PriorityTask): string {
  if (task.needs_alert) return '立即处理'
  if (task.priority_score > 0.5) return '尽快完成'
  if (task.priority_score > 0.3) return '计划安排'
  return '稍后处理'
}
</script>

<template>
  <div class="priority-list">
    <div class="list-header">
      <span class="header-title">优先级任务</span>
      <button class="refresh-btn" @click="fetchPriorityTasks" title="刷新">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M1 4v6h6M23 20v-6h-6" />
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
        </svg>
      </button>
    </div>

    <div v-if="priorityTasks.length === 0" class="empty-state">
      <div class="empty-icon">&#9744;</div>
      <p class="empty-text">暂无待评估任务</p>
      <p class="empty-hint">录入日程后自动评估</p>
    </div>

    <TransitionGroup v-else name="task-list" tag="div" class="task-items">
      <div
        v-for="task in priorityTasks"
        :key="task.id"
        class="task-item"
        :class="{ 'task-urgent': task.needs_alert }"
      >
        <div class="task-score-bar">
          <div
            class="score-fill"
            :class="getScoreBg(task.priority_score)"
            :style="{ width: `${Math.round(task.priority_score * 100)}%` }"
          ></div>
        </div>

        <div class="task-body">
          <div class="task-content">{{ task.content }}</div>
          <div class="task-meta">
            <span class="task-score" :class="getScoreColor(task.priority_score)">
              {{ Math.round(task.priority_score * 100) }}%
            </span>
            <span class="task-category">{{ task.category }}</span>
            <span class="task-label" :class="getScoreColor(task.priority_score)">
              {{ getUrgencyLabel(task) }}
            </span>
          </div>
          <div v-if="task.suggested_action" class="task-action">
            {{ task.suggested_action }}
          </div>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.priority-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 8px;
}

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.refresh-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
}

.refresh-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.05);
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.empty-icon {
  font-size: 28px;
  color: rgba(255, 255, 255, 0.15);
  margin-bottom: 8px;
}

.empty-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.3);
}

.empty-hint {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.15);
  margin-top: 4px;
}

/* Task items */
.task-items {
  overflow-y: auto;
  flex: 1;
}

.task-item {
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transition: background 0.2s;
  border-radius: 6px;
  padding: 8px 8px;
}

.task-item:hover {
  background: rgba(255, 255, 255, 0.03);
}

.task-urgent {
  background: rgba(239, 68, 68, 0.05) !important;
  border-left: 2px solid rgba(239, 68, 68, 0.4);
}

.task-score-bar {
  height: 3px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  margin-bottom: 8px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.task-content {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.4;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.task-score {
  font-size: 11px;
  font-weight: 700;
}

.task-category {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 6px;
  border-radius: 3px;
}

.task-label {
  font-size: 10px;
  font-weight: 500;
}

.task-action {
  font-size: 11px;
  color: rgba(245, 158, 11, 0.7);
  margin-top: 4px;
  font-style: italic;
}

/* List transitions */
.task-list-enter-active {
  animation: slide-in 0.3s ease;
}

.task-list-leave-active {
  animation: slide-in 0.2s ease reverse;
}

@keyframes slide-in {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
</style>
