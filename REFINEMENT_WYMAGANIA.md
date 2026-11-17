# OrderFlow – Wersja A: refinement i kryteria akceptacji

**Źródło:** oficjalny Product Owner, sesja `REF-A-20261117-DP4-7CYCZ4G7`, 17 listopada 2026, 34 pytania / 68 wiadomości. Pełny transkrypt PDF należy dołączyć do raportu; niniejszy dokument nie zastępuje dowodu sesji.

## User Story

Jako pracownik obsługi zamówień chcę anulować zamówienie przez osobny proces w OrderFlow, aby bez ręcznej edycji danych realizować dopuszczone anulowania i otrzymać informację o potrzebie ręcznej obsługi zwrotu.

## Zakres

- Operacja `Anuluj zamówienie` uruchamiana z menu; osobna od standardowej zmiany statusu.
- `NEW`: brak limitu czasu od `created_at`.
- `PAID`: limit **30 minut** od `created_at`.
- `PROCESSING`: limit **15 minut** od `created_at`.
- `SHIPPED`, `DELIVERED`, `CANCELLED`: odmowa bez modyfikacji danych.
- Operacja wymaga potwierdzenia; rezygnacja pozostawia dane bez zmian.
- Po sukcesie modyfikowany jest tylko `status` na `CANCELLED`. Rekord i dane historyczne pozostają dostępne w liście, szczegółach i raporcie.
- `CARD` oraz `TRANSFER`: informacja o konieczności ręcznego zwrotu; `CASH_ON_DELIVERY`: brak takiej informacji.

## Acceptance Criteria – Given / When / Then

1. **AC01** Given status NEW, When pracownik potwierdzi anulowanie, Then status staje się CANCELLED, niezależnie od czasu.
2. **AC02** Given status PAID i wiek zamówienia nieprzekraczający 30 minut, When pracownik potwierdzi, Then status zmienia się na CANCELLED.
3. **AC03** Given status PROCESSING i wiek nieprzekraczający 15 minut, When pracownik potwierdzi, Then status zmienia się na CANCELLED.
4. **AC04** Given PAID powyżej 30 minut lub PROCESSING powyżej 15 minut, When anulowanie zostaje wybrane, Then odmowa bez zapisu.
5. **AC05** Given SHIPPED, DELIVERED lub CANCELLED, When próba anulowania, Then odmowa bez zmian.
6. **AC06** Given anulowanie dopuszczalne, When pracownik nie potwierdzi, Then nie następuje zapis.
7. **AC07** Given anulowanie zakończone sukcesem, When system wyświetla zamówienie i raport, Then rekord pozostaje dostępny, a inne pola pozostają niezmienione.
8. **AC08** Given metoda CARD/TRANSFER, When anulowanie się powiedzie, Then pracownik widzi komunikat o ręcznym zwrocie; dla CASH_ON_DELIVERY komunikat nie jest pokazywany.
9. **AC09** Given niepoprawny lub nieistniejący ID, When próba anulowania, Then komunikat błędu i brak zmian.
10. **AC10** Given ponowne anulowanie CANCELLED, When próba anulowania, Then brak zmian.
11. **AC11** Given standardowa zmiana statusu, When użytkownik obsługuje menu, Then dedykowane anulowanie nie zmienia standardowej macierzy przejść ani nie pozwala nadać CANCELLED standardową opcją.
12. **AC12** Given nieprawidłowa data dla statusu ograniczonego czasowo, When walidacja, Then odmowa bez zapisu (decyzja techniczna chroniąca integralność danych).

## Poza zakresem

Refund automatyczny, integracje z płatnościami i kurierem, zwroty po dostawie, nowe pola `cancelled_at`, `cancelled_by`, `cancellation_reason`, historia statusów, globalny workflow, role, API i baza danych.

## Decyzje techniczne jawnie odróżnione od decyzji PO

- Granica **dokładnie** 15 lub 30 minut jest traktowana jako dozwolona (`<=`); PO powiedział „maksymalnie do”, lecz nie określił osobno precyzji sekund.
- Data ISO bez offsetu jest traktowana jako lokalna, jak w istniejącym OrderFlow; błędne i przyszłe daty są odrzucane dla statusów limitowanych.
- Odczyt zamówienia jest powtarzany po potwierdzeniu; zapis używa istniejącego `save_orders`.
- Istniejący raport nie jest zmieniany: PO nie określił nowej zasady sumowania wartości zamówień anulowanych.
- Przed oddaniem student powinien zweryfikować testy w rzeczywistej gałęzi, przeprowadzić Peer Code Review oraz zachować PR OPEN.
