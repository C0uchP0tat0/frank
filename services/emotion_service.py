# # Use a pipeline as a high-level helper
# from transformers import pipeline

# pipe = pipeline("text-classification", model="Kostya165/rubert_emotion_slicer")

# # пример текста
# # text = "Я очень рад, что участвую в этом проекте!"
# text = "всё номально"

# # прогоняем
# result = pipe(text)
# print(result)

# from transformers import AutoTokenizer, AutoModelForSequenceClassification

# tokenizer = AutoTokenizer.from_pretrained(
#     "Kostya165/rubert_emotion_slicer",
#     cache_folder="./models")
# model = AutoModelForSequenceClassification.from_pretrained(
#     "Kostya165/rubert_emotion_slicer",
#     cache_folder="./models")

from typing import Dict, List
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline


class EmotionService:
    """Сервис для анализа эмоций и тональности ответов кандидата."""

    MODEL_NAME = "Kostya165/rubert_emotion_slicer"

    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME,  cache_dir="./models")
        self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME, cache_dir="./models")
        self.pipe = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            return_all_scores=True
        )

    def analyze(self, text: str) -> Dict[str, float]:
        """
        Анализирует текст и возвращает вероятности по всем эмоциям.
        """
        results = self.pipe(text, truncation=True)
        # pipeline возвращает список с одним элементом (т.к. один текст)
        scores = {item["label"]: item["score"] for item in results[0]}
        return scores

    def best_emotion(self, text: str) -> str:
        """
        Возвращает метку с наибольшей вероятностью.
        """
        scores = self.analyze(text)
        return max(scores, key=scores.get)

    @staticmethod
    def build_context(history: List[Dict[str, str]]) -> str:
        """
        Сжимает историю диалога в текстовый контекст.
        """
        return "\n".join(f"{turn['role'].upper()}: {turn['content']}" for turn in history[-12:])


if __name__ == "__main__":
    service = EmotionService()

   # Маппинг ключей модели на русские эмоции
    labels_map = {
        'aggression': 'агрессия',
        'anxiety': 'тревога',
        'sarcasm': 'сарказм',
        'positive': 'позитив',
        'neutral': 'нейтрально'
    }

    texts = [
        "Я очень рад, что участвую в этом проекте!",
        "Мне тревожно, что дедлайн поджимает.",
        "Я зол, потому что всё сломалось.",
        "Ну окей, посмотрим, что будет дальше.",
        "Мне грустно, что не получилось."
    ]

    for text in texts:
        print(f"\nТекст: {text}")
        scores = service.analyze(text)         # словарь вида {'positive': 0.9, 'neutral': 0.05, ...}
        best = service.best_emotion(text)      # возвращает ключ из scores, например 'positive'

        # Красивый вывод всех эмоций по вероятности
        print("Вероятности по эмоциям:")
        for label, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            print(f"  {labels_map[label]:10} {score:.3f}")

        print(f"➡️ Наиболее вероятная эмоция: {labels_map[best]}")
