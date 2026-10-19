<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { findLegalPage } from '@/lib/legal'

const route = useRoute()
const router = useRouter()
const page = computed(() => findLegalPage(String(route.params.slug ?? '')))

if (!page.value) void router.replace('/')
</script>

<template>
  <div v-if="page">
    <section class="on-red text-white" aria-labelledby="legal-title">
      <div class="page-wrap py-10 lg:py-14">
        <h1 id="legal-title" class="text-4xl font-extrabold sm:text-5xl">{{ page.title }}</h1>
        <p class="mt-3 max-w-xl text-lg">{{ page.intro }}</p>
      </div>
    </section>
    <section class="panel">
      <div class="page-wrap max-w-3xl py-10 lg:py-14">
        <div v-for="section in page.sections" :key="section.heading" class="mb-8">
          <h2 class="text-xl font-bold">{{ section.heading }}</h2>
          <p v-for="(paragraph, index) in section.body" :key="index" class="mt-2 text-lg leading-relaxed">{{ paragraph }}</p>
        </div>
      </div>
    </section>
  </div>
</template>
