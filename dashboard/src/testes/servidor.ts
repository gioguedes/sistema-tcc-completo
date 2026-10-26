import { setupServer } from 'msw/node'
import { handlers } from '@/mocks/handlers'

export const servidor = setupServer(...handlers)
