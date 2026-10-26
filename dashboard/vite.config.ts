/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig, loadEnv } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

const CINCO_MINUTOS = 5 * 60
const SETE_DIAS = 7 * 24 * 60 * 60

/**
 * PWA conforme o TC2 (§9): manifesto instalável e service worker do Workbox.
 * O registro fica em src/app/componentes/AvisoAtualizacao.tsx e só acontece no build sem dados simulados,
 * porque o MSW também usa um service worker no mesmo escopo; com dados simulados, o plugin fica desligado.
 */
const pwa = (desligado: boolean) =>
  VitePWA({
    disable: desligado,
    registerType: 'prompt',
    injectRegister: false,
    // os ícones já entram pelo globPatterns; evita entradas duplicadas no precache
    includeManifestIcons: false,
    manifest: {
      id: '/',
      name: 'Painel Aquícola',
      short_name: 'Aquícola',
      description: 'Monitoramento inteligente da qualidade da água em tanques de piscicultura.',
      lang: 'pt-BR',
      dir: 'ltr',
      start_url: '/',
      scope: '/',
      display: 'standalone',
      orientation: 'any',
      theme_color: '#2F6F73',
      background_color: '#F5F7F6',
      icons: [
        { src: '/icones/icone-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
        { src: '/icones/icone-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
        { src: '/icones/icone-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      // app shell (HTML, JS, CSS, fonte e ícones) com revisão por hash
      globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
      globIgnores: ['mockServiceWorker.js'],
      navigateFallback: '/index.html',
      navigateFallbackDenylist: [/^\/api\//],
      cleanupOutdatedCaches: true,
      // Só GET. Login, alertas, eventos, previsões e todas as escritas vão direto à rede.
      runtimeCaching: [
        {
          // catálogos quase estáticos
          urlPattern: /\/api\/v1\/(especies|tipos-sensor)(\?|$)/,
          handler: 'StaleWhileRevalidate',
          options: {
            cacheName: 'api-catalogos',
            expiration: { maxAgeSeconds: SETE_DIAS },
            cacheableResponse: { statuses: [200] },
          },
        },
        {
          // lista e detalhe de tanques: rede primeiro; sem rede, a cópia de até 5 min
          urlPattern: /\/api\/v1\/tanques(\/\d+)?(\?|$)/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-tanques',
            expiration: { maxAgeSeconds: CINCO_MINUTOS },
            cacheableResponse: { statuses: [200] },
          },
        },
        {
          // série temporal: cópia curta, para não exibir dado antigo como atual
          urlPattern: /\/api\/v1\/tanques\/\d+\/leituras/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-leituras',
            expiration: { maxAgeSeconds: CINCO_MINUTOS, maxEntries: 30 },
            cacheableResponse: { statuses: [200] },
          },
        },
      ],
    },
  })

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react(), tailwindcss(), pwa(env.VITE_USAR_MOCKS === 'true')],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      // Mesma origem para a API: o cookie de renovação (SameSite=Strict) funciona e o CORS fica desnecessário.
      proxy: env.API_PROXY_ALVO ? { '/api': { target: env.API_PROXY_ALVO, changeOrigin: true } } : undefined,
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/testes/configuracao.ts'],
      css: false,
    },
  }
})
