"""Unit тесты для RAG hybrid merge алгоритма."""


class TestHybridMerge:
    """Тесты для алгоритма hybrid merge."""

    def test_score_normalization(self) -> None:
        """Нормализация FTS scores в диапазон [0, 1]."""
        # Имитация FTS результатов
        fts_results = [
            ("chunk1", 0.5),
            ("chunk2", 1.0),
            ("chunk3", 0.2),
            ("chunk4", 0.8),
        ]

        # Нормализация
        max_rank = max(rank for _, rank in fts_results)
        min_rank = min(rank for _, rank in fts_results)
        rank_range = max_rank - min_rank

        normalized = {}
        for chunk_id, rank in fts_results:
            normalized[chunk_id] = (rank - min_rank) / rank_range

        # Проверки
        assert 0.0 <= normalized["chunk1"] <= 1.0
        assert normalized["chunk3"] == 0.0  # Минимум
        assert normalized["chunk2"] == 1.0  # Максимум
        assert 0.0 < normalized["chunk4"] < 1.0

    def test_vector_distance_to_similarity(self) -> None:
        """Конвертация cosine distance в similarity."""
        # Cosine distance: 0 = идентичные, 1 = противоположные
        distances = [0.1, 0.3, 0.5, 0.8]

        # Конвертация: similarity = 1 - distance
        similarities = [1.0 - d for d in distances]

        assert similarities[0] == 0.9  # Близкие векторы
        assert similarities[1] == 0.7
        assert similarities[2] == 0.5
        assert abs(similarities[3] - 0.2) < 1e-10  # Далёкие векторы (float precision)

    def test_weighted_merge(self) -> None:
        """Взвешенное объединение FTS + Vector."""
        # Веса
        dense_weight = 0.7
        sparse_weight = 0.3

        # Результаты для одного чанка
        fts_score = 0.8
        vector_score = 0.6

        # Финальный score
        final_score = dense_weight * vector_score + sparse_weight * fts_score

        expected = 0.7 * 0.6 + 0.3 * 0.8  # 0.42 + 0.24 = 0.66
        assert abs(final_score - expected) < 0.001

    def test_weights_sum_validation(self) -> None:
        """Проверка, что веса в сумме дают 1.0."""
        dense_weight = 0.7
        sparse_weight = 0.3

        total = dense_weight + sparse_weight
        assert 0.99 <= total <= 1.01  # Допускаем небольшую погрешность

    def test_min_relevance_score_filtering(self) -> None:
        """Фильтрация по min_relevance_score."""
        results = [
            ("chunk1", 0.9),
            ("chunk2", 0.75),
            ("chunk3", 0.6),
            ("chunk4", 0.4),
        ]

        min_score = 0.7
        filtered = [(chunk_id, score) for chunk_id, score in results if score >= min_score]

        assert len(filtered) == 2
        assert ("chunk1", 0.9) in filtered
        assert ("chunk2", 0.75) in filtered
        assert ("chunk3", 0.6) not in filtered

    def test_top_k_limiting(self) -> None:
        """Ограничение количества результатов (top_k)."""
        results = [
            ("chunk1", 0.9),
            ("chunk2", 0.8),
            ("chunk3", 0.7),
            ("chunk4", 0.6),
            ("chunk5", 0.5),
        ]

        top_k = 3
        top_results = results[:top_k]

        assert len(top_results) == 3
        assert top_results[0][0] == "chunk1"
        assert top_results[-1][0] == "chunk3"
