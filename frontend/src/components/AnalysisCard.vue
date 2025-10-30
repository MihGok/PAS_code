<template>
  <article class="analysis-card">
    <h3>
      Анализ #{{ localAnalysis.examination_id }} от {{ localAnalysis.examination_date }}
    </h3>
    <div class="analysis-grid">
      <div>
        <img :src="imageUrl" alt="Снимок анализа" class="analysis-image">
        <h4>Результат модели</h4>
        <ul>
          <li><strong>Результат:</strong> {{ getDiseaseName(localAnalysis.examination_result_model) }} ({{ localAnalysis.examination_result_model }})</li>
          <li><strong>Уверенность:</strong> {{ (localAnalysis.model_confidence * 100).toFixed(1) }}%</li>
          <li><strong>Локация:</strong> {{ getLocationName(localAnalysis.examination_location) }} ({{ localAnalysis.examination_location || 'N/A' }})</li>
        </ul>
      </div>

      <div>
        <div class="diagnoses-section">
          <h4>Диагнозы врачей</h4>

          <div v-if="Object.keys(groupedDiagnoses).length === 0">
            <p>Диагнозы еще не поставлены.</p>
          </div>

          <div v-for="(group, result) in groupedDiagnoses" :key="result" class="diagnosis-group">
            <div class="diagnosis-header">
              {{ getDiseaseName(result) }} ({{ result }}): {{ group.count }}
              <span
                class="toggle-doctors"
                @click="toggleDoctors(result)">
                ({{ visibleDoctors[result] ? 'скрыть' : 'показать' }} список)
              </span>
            </div>
            <ul v-if="visibleDoctors[result]" class="diagnosis-doctors-list">
              <li v-for="(doctor, index) in group.doctors" :key="index">
                {{ doctor }}
              </li>
            </ul>
          </div>

          <form @submit.prevent="addNewDiagnosis" class="add-diagnosis-form">
            <div class="form-group" style="flex: 1;">
              <label :for="'diag_result_' + localAnalysis.examination_id" style="font-weight: normal; font-size: 0.9em;">Добавить диагноз:</label>
              <select :id="'diag_result_' + localAnalysis.examination_id" v-model="newDiagnosis.diagnosis_result" required>
                  <option v-for="diag in diseaseOptions" :key="diag.value" :value="diag.value">
                      {{ diag.text }} ({{ diag.value }})
                  </option>
              </select>
            </div>
            <div class="form-group" style="flex: 1;">
              <label :for="'diag_doctor_' + localAnalysis.examination_id" style="font-weight: normal; font-size: 0.9em;">Имя врача:</label>
              <input :id="'diag_doctor_' + localAnalysis.examination_id" v-model="newDiagnosis.doctor_name" type="text" placeholder="ФИО врача" required>
            </div>
            <button type="submit" :disabled="isAdding" style="align-self: flex-end;">
              {{ isAdding ? '...' : 'OK' }}
            </button>
          </form>
          <div v-if="addError" class="status-message error" style="font-size: 0.9em; padding: 8px;">
            {{ addError }}
          </div>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import axios from 'axios'
// Импортируем diseaseOptions для выпадающего списка
import { diseaseMap, locationMap, diseaseOptions } from '../dictionaries'

// --- Вспомогательные функции для перевода ---
function getDiseaseName(key) {
    return diseaseMap[key] || key;
}

function getLocationName(key) {
    return locationMap[key] || key;
}

const props = defineProps({
  analysis: {
    type: Object,
    required: true
  }
})

const localAnalysis = ref(JSON.parse(JSON.stringify(props.analysis)))
const isAdding = ref(false)
const addError = ref('')

const imageUrl = computed(() => {
  return `/api/image/${localAnalysis.value.image.image_id}/`
})

// Группировка диагнозов (используются коды, как они приходят из БД)
const groupedDiagnoses = computed(() => {
  const groups = {}
  for (const diag of localAnalysis.value.diagnoses) {
    const result = diag.diagnosis_result
    const doctor = diag.doctor_name
    if (!groups[result]) {
      groups[result] = { count: 0, doctors: [] }
    }
    groups[result].count++
    groups[result].doctors.push(doctor)
  }
  return groups
})

const visibleDoctors = reactive({})
function toggleDoctors(resultKey) {
  visibleDoctors[resultKey] = !visibleDoctors[resultKey]
}

const newDiagnosis = reactive({
  diagnosis_result: 'NV', // Код по умолчанию (из списка)
  doctor_name: ''
})

async function addNewDiagnosis() {
  isAdding.value = true
  addError.value = ''
  try {
    const response = await axios.post(
      `/api/analysis/${localAnalysis.value.examination_id}/diagnoses/`,
      {
        diagnosis_result: newDiagnosis.diagnosis_result,
        doctor_name: newDiagnosis.doctor_name
      }
    )
    localAnalysis.value.diagnoses.push(response.data)
    newDiagnosis.doctor_name = ''
  } catch (error) {
    console.error('Ошибка при добавлении диагноза:', error)
    addError.value = 'Не удалось добавить диагноз.'
  } finally {
    isAdding.value = false
  }
}
</script>

<style scoped>
/* (Стили остаются без изменений) */
.analysis-card {
  border: 1px solid #ccc;
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  background-color: white;
}

h3 {
  color: #007bff;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

h4 {
  color: #333;
  margin-top: 15px;
  margin-bottom: 10px;
  font-size: 1em;
}

.analysis-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 30px;
}

.analysis-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin-bottom: 15px;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

li {
  margin-bottom: 5px;
  font-size: 0.95em;
}

.diagnoses-section {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px solid #eee;
}

.diagnosis-group {
  margin-bottom: 10px;
  padding: 8px;
  background-color: #e9f5ff;
  border-left: 3px solid #007bff;
  border-radius: 4px;
}

.diagnosis-header {
  font-weight: bold;
  color: #0056b3;
}

.toggle-doctors {
  font-weight: normal;
  font-size: 0.8em;
  color: #666;
  cursor: pointer;
  margin-left: 10px;
}

.diagnosis-doctors-list {
  list-style-type: disc;
  margin-left: 20px;
  margin-top: 5px;
  font-weight: normal;
  font-size: 0.9em;
}

.add-diagnosis-form {
  display: flex;
  gap: 10px;
  margin-top: 15px;
  align-items: flex-end;
}

.add-diagnosis-form input,
.add-diagnosis-form select,
.add-diagnosis-form button {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.add-diagnosis-form button {
  background-color: #28a745;
  color: white;
  border: none;
  cursor: pointer;
}

.add-diagnosis-form button:disabled {
  background-color: #90ee90;
  cursor: not-allowed;
}

.status-message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
</style>