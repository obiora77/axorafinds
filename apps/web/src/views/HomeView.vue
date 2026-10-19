<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import HeroChoice from '@/components/HeroChoice.vue'
import PropertyCard from '@/components/PropertyCard.vue'
import { buttonMotion, gridStagger, heroIn, reveal } from '@/plugins/motion'
import { useAuthStore } from '@/stores/auth'
import { usePropertiesStore } from '@/stores/properties'

const router = useRouter()
const auth = useAuthStore()
const store = usePropertiesStore()
const choice = ref<'find' | 'list'>('find')

onMounted(() => {
  void store.fetchLatest(4)
})

async function getStarted(): Promise<void> {
  if (choice.value === 'find') {
    await router.push('/properties')
  } else if (auth.isAuthed) {
    await router.push('/list-property')
  } else {
    await router.push({ name: 'signup', query: { role: 'owner', redirect: '/list-property' } })
  }
}
</script>

<template>
  <div>
    <section class="on-red text-white" aria-labelledby="hero-title">
      <div class="page-wrap grid items-center gap-10 py-10 lg:grid-cols-2 lg:gap-14 lg:py-16">
        <div v-motion v-bind="heroIn(0)">
          <h1 id="hero-title" class="text-4xl font-extrabold leading-[1.05] sm:text-5xl lg:text-6xl">
            How will you use Axora?
          </h1>
          <p class="mt-4 max-w-md text-lg">Verified homes, simple inspections, and no pile of agent fees.</p>
          <div class="mt-7">
            <HeroChoice v-model="choice" />
          </div>
          <button type="button" v-motion v-bind="buttonMotion()" class="btn btn-light mt-6 w-full px-10 sm:w-auto" @click="getStarted">
            Get Started
          </button>
        </div>

        <div v-motion v-bind="heroIn(120)" class="flex flex-col items-center text-center">
          <img src="/hero-house.svg" alt="" width="520" height="400" class="w-full max-w-md" />
          <h2 class="mt-4 text-3xl font-extrabold">Find Verified Properties</h2>
          <p class="mt-2 max-w-sm">Every listing is reviewed by our team before it goes live.</p>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="latest-title">
      <div class="page-wrap py-10 lg:py-14">
        <div v-motion v-bind="reveal()" class="flex flex-wrap items-end justify-between gap-3">
          <h2 id="latest-title" class="text-2xl font-extrabold sm:text-3xl">Latest listings</h2>
          <RouterLink to="/properties" class="inline-flex min-h-11 items-center font-semibold text-brand hover:underline">
            View all properties
          </RouterLink>
        </div>

        <p v-if="store.latestLoading && !store.latest.length" class="mt-6 text-muted" role="status">Loading listings...</p>
        <p v-else-if="store.latestError" class="mt-6 font-medium text-brand" role="alert">{{ store.latestError }}</p>
        <p v-else-if="!store.latest.length" class="mt-6 text-muted">No listings yet. Check back soon.</p>

        <TransitionGroup
          v-if="store.latest.length"
          tag="ul"
          appear
          :css="false"
          class="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
          @before-enter="gridStagger.onBeforeEnter"
          @enter="gridStagger.onEnter"
          @before-appear="gridStagger.onBeforeEnter"
          @appear="gridStagger.onEnter"
        >
          <li v-for="(property, index) in store.latest" :key="property.id" :data-index="index">
            <PropertyCard :property="property" />
          </li>
        </TransitionGroup>
      </div>
    </section>
  </div>
</template>
