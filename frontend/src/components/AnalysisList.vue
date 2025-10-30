<template>
  <div class="analysis-list-container">
    <h2>Просмотр анализов пациента</h2>

    <div class="form-group" style="max-width: 400px; margin-bottom: 20px;">
      <label for="search_user_id">Введите СНИЛС пациента</label>
      <div style="display: flex; gap: 10px;">
        <input id="search_user_id" v-model="searchUserId" type="text" placeholder="123-456-789 00">
        <button @click="fetchAnalyses" :disabled="isLoading">
          {{ isLoading ? 'Поиск...' : 'Найти' }}
        </button>
      </div>
    </div>

    <div v-if="statusMessage"
         :class="['status-message', statusType]">
      {{ statusMessage }}
    </div>

    <div class="analysis-list" v-if="analyses.length > 0">
      <AnalysisCard
        v-for="analysis in analyses"
        :key="analysis.examination_id"
        :analysis="analysis"
      />
    </div>
    <div v-else-if="!isLoading && searchAttempted">
      <p>Анализы для этого СНИЛС не найдены.</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import AnalysisCard from './AnalysisCard.vue'

const searchUserId = ref('')
const analyses = ref([])
const isLoading = ref(false)
const searchAttempted = ref(false) // Флаг, что поиск уже был
const statusMessage = ref('')
const statusType = ref('')

async function fetchAnalyses() {
  if (!searchUserId.value) {
    statusMessage.value = 'Пожалуйста, введите СНИЛС.'
    statusType.value = 'error'
    return
  }

  isLoading.value = true
  searchAttempted.value = true
  statusMessage.value = ''
  analyses.value = [] // Очищаем старые

  try {
    // Используем относительный путь
    const response = await axios.get(`/api/user/${searchUserId.value}/examinations/`)
    analyses.value = response.data

    if (analyses.value.length === 0) {
      statusMessage.value = 'Анализы не найдены.'
      statusType.value = 'success' // Это не ошибка, это успешный пустой ответ
    }

  } catch (error) {
    console.error('Ошибка при загрузке анализов:', error)
    if (error.response && error.response.status === 404) {
      statusMessage.value = 'Пользователь с таким СНИЛС не найден.'
    } else {
      statusMessage.value = 'Не удалось загрузить данные.'
    }
    statusType.value = 'error'
  } finally {
    isLoading.value = false
  }
}
</script>