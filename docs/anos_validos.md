# Valid years: rules and reasons

Source: validation in `src/validar.py` (B4) and queries in `src/banco.py` (B5).

## 1. Enrollments (`matriculas_total`): 2018–2026 (all years)
- Reason: the total number of students is filled in every year, and the validation found 0 errors.
- Note: there is no 2025 file at the source.

## 2. Approval and failure rates: 2018–2023
- Cut 2024: about 84% of the students are still "Cursando" (184,949 of 220,926).
  The final results were not recorded, and 379 of 461 schools have base = 0.
- Cut 2026: the school year isn't over, so there are 0 approved, 0 failed, 0 dropouts,
  and all 460 schools have base = 0.
- Note: from 2020 on, the approval rate may be a bit higher than the real one.
  Dropouts were not counted, so they are missing from the base.

## 3. Dropout rate: 2018 only
- Cut 2019: dropout fell 98.5% in one year (10,490 → 158), while enrollments fell
  only 10%. This is probably a data entry error.
- Cut 2020–2026: dropout is 0 in every school. The column was probably no longer filled in.

## 4. Outside the valid years
- The rate is shown as "not available" (`None`), never as 0%. A 0% would be false information.

## 5. Where the rule lives
- In `src/banco.py`, as the constants `ANOS_TAXA_APROVACAO` and `ANOS_TAXA_ABANDONO`.
- Reason: anyone who uses the queries, with or without the dashboard, gets the same correct answer.

## Effect on the dashboard
- The comparison cards show 2023 vs. 2018 instead of the current year.
