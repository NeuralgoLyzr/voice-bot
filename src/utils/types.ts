export enum Path {
  HOME = '/',
  CHATBOT = '/chatbot',
  CREATE_CHATBOT = '/create-chatbot',
}

export interface IChatbot {
  id: string
  created_at: string
  name: string
  knowledge_id: string
  user: string
  type: string
  slug: any
  welcome_message: any
  model: string
  temperature: number
  top_p: number
  company_slug: any
}

export enum UserType {
  assistant =   'assistant',
  user = 'user'
}

export enum BotType {
  CHATBOT = 'CHAT',
  QA = 'QA'
}