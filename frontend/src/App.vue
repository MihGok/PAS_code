<template>
  <header>
    <h1>Панель медицинских анализов</h1>
  </header>

  <main>
    <AnalysisForm />

    <hr class="section-divider">

    <AnalysisList />
  </main>
</template>

<script setup>
import AnalysisForm from './components/AnalysisForm.vue'
import AnalysisList from './components/AnalysisList.vue'
</script>

<style>
/* Общие стили для приложения */
body {
  font-family: Arial, sans-serif;
  background-color: #f4f4f4;
  color: #333;
  margin: 0;
  padding: 0;
}

header {
  background-color: #007bff;
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h1 {
  margin: 0;
  font-size: 1.8em;
}

main {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.section-divider {
  border: none;
  border-top: 2px solid #e0e0e0;
  margin: 40px 0;
}
</style>