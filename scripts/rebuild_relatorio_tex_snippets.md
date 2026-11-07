# Rebuild notes

To regenerate missing LaTeX sections from question sources:

1. Clean markdown lives in `tmp/_qXX_clean.md` (generated from docs/ or src/*/README.md).
2. Convert with: `pandoc -f gfm+tex_math_dollars -t latex --wrap=none`.
3. Copy figures from `src/**/figures/` into `figures/`.
4. Keep hand-written Q1, Q2, Q3, Q5, Q11; splice Q4, Q6–Q10, Q12–Q15.
5. Disable babel `"` shorthand: `\AtBeginDocument{\shorthandoff{"}}`.
6. Compile: `tectonic lista2_ia_ufal.tex`.
