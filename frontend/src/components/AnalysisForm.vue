<template>
  <div class="analysis-form-container">
    <h2>Новый анализ пациента</h2>

    <div v-if="statusMessage"
         :class="['status-message', statusType]">
      {{ statusMessage }}
    </div>

    <form @submit.prevent="submitAnalysis">
      <section class="form-section">
        <h3>Данные пользователя</h3>
        <div class="form-grid">
          <div class="form-group">
            <label for="user_id">СНИЛС (ID)</label>
            <input id="user_id" v-model="formData.user_id" type="text" required>
          </div>
          <div class="form-group">
            <label for="user_second_name">Фамилия</label>
            <input id="user_second_name" v-model="formData.user_second_name" type="text" required>
          </div>
          <div class="form-group">
            <label for="user_name">Имя</label>
            <input id="user_name" v-model="formData.user_name" type="text" required>
          </div>
          <div class="form-group">
            <label for="user_patronomyc">Отчество</label>
            <input id="user_patronomyc" v-model="formData.user_patronomyc" type="text">
          </div>
          <div class="form-group">
            <label for="user_age">Возраст</label>
            <input id="user_age" v-model.number="formData.user_age" type="number" required>
          </div>
          <div class="form-group">
            <label for="user_gender">Пол</label>
            <select id="user_gender" v-model="formData.user_gender" required>
              <option :value="true">Мужской</option>
              <option :value="false">Женский</option>
            </select>
          </div>
        </div>
      </section>

      <section class="form-section">
        <h3>Детали обследования</h3>
        <div class="image-analysis-container">
          <div class="image-upload-preview">
            <div class="form-group">
              <label for="image_file">Снимок для анализа</label>
              <input id="image_file" @change="handleFileUpload" type="file" accept="image/*" required :disabled="isAnalyzing">
            </div>
            <div class="image-preview" v-if="imagePreviewUrl">
              <img :src="imagePreviewUrl" alt="Превью загруженного снимка">
            </div>
            <button
                type="button"
                @click="runAnalysis"
                :disabled="!formData.image_file || isAnalyzing"
                class="analyze-button">
              {{ isAnalyzing ? 'Анализ...' : 'Провести анализ модели' }}
            </button>
          </div>

          <div class="examination-fields">
            <div class="form-grid">
              <div class="form-group">
                <label for="examination_result_model">Предсказание модели</label>
                <input id="examination_result_model"
                       :value="formData.examination_result_model ? `${getDiseaseName(formData.examination_result_model)} (${formData.examination_result_model})` : 'Нет данных'"
                       type="text"
                       readonly
                       :class="{ 'result-ok': formData.examination_result_model }">
              </div>
              <div class="form-group">
                <label for="model_confidence">Уверенность модели</label>
                <input id="model_confidence"
                       :value="formData.model_confidence ? (formData.model_confidence * 100).toFixed(2) + '%' : 'Нет данных'"
                       type="text"
                       readonly
                       :class="{ 'result-ok': formData.model_confidence }">
              </div>

              <div class="form-group">
                <label for="examination_location">Локация поражения (код)</label>
                <select id="examination_location" v-model="formData.examination_location" required>
                  <option v-for="loc in locationOptions" :key="loc.value" :value="loc.value">
                      {{ loc.text }} ({{ loc.value }})
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label for="examination_doctor">Врач, проводивший осмотр</label>
                <input id="examination_doctor" v-model="formData.examination_doctor" type="text" required>
              </div>

              <div class="form-group">
                <label for="diagnosis_result">Первичный диагноз (врача)</label>
                <select id="diagnosis_result" v-model="formData.diagnosis_result" required>
                  <option v-for="disease in diseaseOptions" :key="disease.value" :value="disease.value">
                      {{ disease.text }} ({{ disease.value }})
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </section>

      <button type="submit" :disabled="isSubmitting || !formData.examination_result_model">
        {{ isSubmitting ? 'Создание...' : 'Создать анализ' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import axios from 'axios'
import { locationOptions, diseaseOptions, diseaseMap } from '../dictionaries'

// --- State ---
const formData = reactive({
  // User Data
  user_id: '',
  user_name: '',
  user_second_name: '',
  user_patronomyc: '',
  user_gender: true,
  user_age: null,

  // Examination Data
  image_file: null,
  examination_location: 'TR',
  examination_doctor: '',

  // Model Prediction (Filled by runAnalysis)
  examination_result_model: '', // Empty until analysis
  model_confidence: null,       // Empty until analysis

  // Initial Doctor Diagnosis (maps to diagnosis_result)
  diagnosis_result: 'NV', // Default to Nevus
})

const imagePreviewUrl = ref(null)
const isSubmitting = ref(false)
const isAnalyzing = ref(false)
const statusMessage = ref('')
const statusType = ref('')

// --- Methods ---

// Helper function to get disease name from code
function getDiseaseName(code) {
    return diseaseMap[code] || code;
}

function handleFileUpload(event) {
  const file = event.target.files[0]
  if (file) {
    formData.image_file = file
    // Создание URL для превью (Требование 3)
    imagePreviewUrl.value = URL.createObjectURL(file)

    // Сброс результатов модели при загрузке нового файла
    formData.examination_result_model = ''
    formData.model_confidence = null
  } else {
    formData.image_file = null
    imagePreviewUrl.value = null
  }
}

function resetForm() {
  // ... (reset logic remains the same) ...
  formData.user_id = ''
  formData.user_name = ''
  formData.user_second_name = ''
  formData.user_patronomyc = ''
  formData.user_gender = true
  formData.user_age = null

  formData.image_file = null
  formData.examination_result_model = ''
  formData.model_confidence = null
  formData.examination_location = 'TR'
  formData.examination_doctor = ''
  formData.diagnosis_result = 'NV'

  // Сброс превью
  imagePreviewUrl.value = null
  // Сброс поля файла вручную
  const fileInput = document.getElementById('image_file')
  if (fileInput) fileInput.value = null
}

async function runAnalysis() {
  if (!formData.image_file) {
    statusMessage.value = 'Пожалуйста, выберите файл изображения для анализа.'
    statusType.value = 'error'
    return
  }

  isAnalyzing.value = true
  statusMessage.value = 'Выполняется анализ изображения...'
  statusType.value = 'info'

  const analysisData = new FormData()
  analysisData.append('image_file', formData.image_file)

  try {
    // Вызов нового эндпоинта /api/analyze/ (Требование 1)
    const response = await axios.post('/api/analyze/', analysisData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    // Заполнение полей результатами модели
    formData.examination_result_model = response.data.examination_result_model
    formData.model_confidence = response.data.model_confidence

    statusMessage.value = `✅ Анализ завершен: ${getDiseaseName(formData.examination_result_model)} с уверенностью ${(formData.model_confidence * 100).toFixed(2)}%.`
    statusType.value = 'success'

  } catch (error) {
    console.error('Ошибка при проведении анализа:', error)
    const detail = error.response?.data?.detail || 'Произошла ошибка при анализе изображения.'
    statusMessage.value = `❌ Ошибка анализа: ${detail}`
    statusType.value = 'error'
    // Сброс результатов в случае ошибки
    formData.examination_result_model = ''
    formData.model_confidence = null
  } finally {
    isAnalyzing.value = false
  }
}


async function submitAnalysis() {
  // Дополнительная проверка, что анализ был проведен
  if (!formData.examination_result_model) {
    statusMessage.value = 'Сначала проведите анализ изображения.'
    statusType.value = 'error'
    return
  }

  isSubmitting.value = true
  statusMessage.value = ''
  statusType.value = ''

  const data = new FormData()

  // 1. Добавляем файл
  data.append('image_file', formData.image_file)

  // 2. Добавляем все остальные поля
  // ИЗМЕНЕНИЕ: Теперь мы отправляем только те поля, которые ожидает бэкенд
  // Backend ожидает: user_id, user_name, ..., examination_location, examination_doctor,
  // examination_result_model, model_confidence, diagnosis_result, doctor_name, image_file

  // User Data
  data.append('user_id', formData.user_id)
  data.append('user_name', formData.user_name)
  data.append('user_second_name', formData.user_second_name)
  if (formData.user_patronomyc) data.append('user_patronomyc', formData.user_patronomyc)
  data.append('user_gender', formData.user_gender)
  data.append('user_age', formData.user_age)

  // Examination Data
  if (formData.examination_location) data.append('examination_location', formData.examination_location)
  data.append('examination_doctor', formData.examination_doctor)

  // Model Results (Требование 1)
  data.append('examination_result_model', formData.examination_result_model)
  // model_confidence должен быть строкой для FormData
  data.append('model_confidence', formData.model_confidence)

  // Initial Diagnosis Data
  data.append('diagnosis_result', formData.diagnosis_result) // Код диагноза (NV, MEL и т.д.)
  data.append('doctor_name', formData.examination_doctor) // Используем examination_doctor как doctor_name

  // 3. Отправляем запрос
  try {
    const response = await axios.post('/api/analysis/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    statusMessage.value = `✅ Анализ (ID: ${response.data.examination_id}) успешно создан!`
    statusType.value = 'success'
    resetForm() // Очищаем форму

  } catch (error) {
    console.error('Ошибка при создании анализа:', error.response || error)
    let detail = 'Произошла неизвестная ошибка.'
    // Дополнительный разбор ошибки 422 для диагностики
    if (error.response && error.response.status === 422) {
        detail = 'Ошибка валидации данных. Проверьте все поля формы.'
        if (error.response.data && error.response.data.detail) {
             detail += ': ' + error.response.data.detail.map(d => `${d.loc.slice(-1)} - ${d.msg}`).join(', ')
        }
    } else if (error.response && error.response.data && error.response.data.detail) {
      detail = error.response.data.detail
    }
    statusMessage.value = `❌ Ошибка при создании анализа: ${detail}`
    statusType.value = 'error'

  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
/* Ваши стили */
.analysis-form-container {
  max-width: 1000px; /* Увеличим ширину для нового лейаута */
  margin: 0 auto 40px;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  color: #333;
  border-bottom: 2px solid #ddd;
  padding-bottom: 10px;
  margin-bottom: 20px;
}

h3 {
  color: #555;
  margin-top: 15px;
  margin-bottom: 10px;
  font-size: 1.1em;
}

.form-section {
    margin-bottom: 25px;
    padding: 15px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background-color: white;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

label {
  margin-bottom: 5px;
  font-weight: bold;
  font-size: 0.9em;
  color: #444;
}

input[type="text"],
input[type="number"],
select {
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1em;
  width: 100%;
  box-sizing: border-box;
}

/* Стили для разделения блока анализа и изображения */
.image-analysis-container {
    display: flex;
    gap: 30px;
}

.image-upload-preview {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 15px;
    border-right: 1px solid #e0e0e0;
    padding-right: 30px;
}

.examination-fields {
    flex: 2;
}

.image-preview {
    width: 100%;
    max-width: 250px;
    height: 250px;
    border: 2px dashed #007bff;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 4px;
    overflow: hidden;
}

.image-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.analyze-button {
    background-color: #ffc107;
    color: #333;
    padding: 10px 15px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: background-color 0.3s;
}

.analyze-button:hover:not(:disabled) {
    background-color: #e0a800;
}

.analyze-button:disabled {
    background-color: #ffe08a;
    cursor: not-allowed;
}

input[type="file"] {
  padding: 5px;
}

/* Стили для результатов модели */
input[readonly] {
    background-color: #eee;
    font-weight: bold;
}

.result-ok {
    background-color: #d4edda !important; /* Зеленый фон для заполненных результатов */
    color: #155724;
}

button[type="submit"] {
  background-color: #007bff;
  color: white;
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 30px;
  font-size: 1.1em;
  transition: background-color 0.3s;
}

button[type="submit"]:hover:not(:disabled) {
  background-color: #0056b3;
}

button[type="submit"]:disabled {
  background-color: #99cfff;
  cursor: not-allowed;
}

.status-message {
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;
  font-weight: bold;
}

.status-message.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-message.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.status-message.info {
  background-color: #cce5ff;
  color: #004085;
  border: 1px solid #b8daff;
}
</style>