# Модуль для использования обученной модели в боте предоставляет функции для загрузки модели и получения предсказаний
import os
from typing import Tuple, Optional
import requests
from ai_module.train import PetStoreIntentClassifier  

# Настройка клиента YandexGPT
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Менеджер для управления загрузкой и использованием ИИ-модели, используем для реализации  паттерна Singleton для эффективного использования памяти 
class AIModelManager:
        
    _instance = None
    _classifier = None
    
    # Реализация паттерна Singleton
    def __new__(cls):
        
        if cls._instance is None:
            cls._instance = super(AIModelManager, cls).__new__(cls)
        return cls._instance
    
    # Инициализация менеджера модели
    def __init__(self):
        
        self.model_path = os.getenv('AI_MODEL_PATH', 'ai_model/pet_store_model_v3_fixed')
        self._classifier = None

    #  Загрузим обученную модель   
    def load_model(self) -> Optional[PetStoreIntentClassifier]:
        if self._classifier is not None:
            return self._classifier
            
        try:
            if os.path.exists(self.model_path):
                self._classifier = PetStoreIntentClassifier.load_from_file(self.model_path)
                print(f"Модель успешно загружена из {self.model_path}")
                return self._classifier
            else:
                print(f"Модель не найдена по пути {self.model_path}")
                return None
        except Exception as e:
            print(f"Ошибка при загрузке модели: {e}")
            return None
    
    # Предсказание намерения для текстового запроса
    def predict_user_intent(self, user_text: str) -> Tuple[str, float]:
        classifier = self.load_model()
        if classifier is None:
            # Если модель не загружена, возвращаем "other" с низкой уверенностью
            return "other", 0.0   
        return classifier.predict(user_text)
    
    # Проверка загружена ли модель
    def is_model_loaded(self) -> bool:
        return self._classifier is not None

def ask_yandexgpt(user_message: str, system_prompt: str = None) -> str:
    
    # Отправляет запрос к YandexGPT и возвращает ответ
    if system_prompt is None:
        system_prompt = (
            "Ты — полезный ассистент зоомагазина «Четыре Лапы». "
            "Твоя задача — помогать покупателям выбирать товары для животных, "
            "отвечать на вопросы о кормах, аксессуарах, уходе за питомцами. "
            "Отвечай дружелюбно, но по делу. "
            "Если не знаешь ответа — предложи обратиться к живому консультанту."
        )

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 2000
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_message}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['result']['alternatives'][0]['message']['text']
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети при обращении к YandexGPT: {e}")
        return "Извините, произошла ошибка сети. Попробуйте позже или обратитесь к оператору."
    except KeyError as e:
        print(f"Ошибка парсинга ответа YandexGPT: {e}")
        return "Извините, неверный формат ответа от сервера. Попробуйте позже."
    except Exception as e:
        print(f"Неожиданная ошибка при обращении к YandexGPT: {e}")
        return "Извините, произошла неизвестная ошибка. Попробуйте позже или обратитесь к оператору."

# Основная функция для получения ответа от ИИ, использующаяся в обработчиках бота для генерации ответов
def get_bot_response(user_message: str) -> dict:
    """
    Гибридный подход:
    1. Сначала классифицируем намерение через обученную нейросеть
    2. Для сложных запросов или низкой уверенности — обращаемся к YandexGPT
    """
    manager = AIModelManager()
    intent, confidence = manager.predict_user_intent(user_message)
    
    # Шаблоны ответов для каждого намерения
    response_templates = {
        "find_product": "Я помогу вам найти нужный товар. Какой именно товар вас интересует?",
        "get_product_info": "Я предоставлю информацию о товаре. Укажите, пожалуйста, название или артикул.",
        "check_price": "Цена на данный товар составляет... (уточните товар)",
        "check_availability": "Проверю наличие товара. Какой товар вас интересует?",
        "get_care_advice": "Я подскажу по уходу за питомцем. Что именно вас интересует?",
        "ask_delivery": "Информация о доставке: мы доставляем по всей России...",
        "ask_payment": "Способы оплаты: картой онлайн, наличными при получении...",
        "ask_promotions": "Сейчас действуют акции на корма и аксессуары...",
        "greeting": "Здравствуйте! Я бот-помощник зоомагазина 'Четыре Лапы'. Чем могу помочь?",
        "goodbye": "До свидания! Будем рады видеть вас снова!",
        "help": "Я могу помочь с поиском товаров, информацией о доставке и оплате...",
        "other": "Извините, я не совсем понял ваш запрос. Попробуйте переформулировать или воспользуйтесь командой /help"
    }
    
    response_text = response_templates.get(intent)

    if response_text is None or confidence < 0.6:
        response_text = ask_yandexgpt(user_message)

    return {
        "intent": intent,
        "confidence": confidence,
        "response": response_text
    }

def get_ai_response(query: str) -> dict:
    return get_bot_response(query)
