# Personas datu apstrādes politika (GDPR-001)

Šis dokuments apraksta personas datu apstrādi platformā Skaitītāji un ir
minimāla apstrādes reģistra versija (pēc analoģijas ar ds-riga reģistru).

## 1. Apstrādes reģistrs (Article 30)

| Apstrāde | Datu subjekts | Datu kategorijas | Juridiskais pamats | Glabāšanas termiņš |
|----------|---------------|------------------|--------------------|--------------------|
| Iedzīvotāju konti | Iedzīvotājs | e-pasts, vārds, tālrunis, loma | Līgums / leģitīmas intereses | Kamēr aktīvs konts + 12 mēn. |
| Dzīvokļu piesaiste | Iedzīvotājs | saite lietotājs↔dzīvoklis | Līgums | Kamēr aktīvs konts |
| Skaitītāju rādījumi | Iedzīvotājs | rādījums, periods, patēriņš, iesniedzējs | Leģitīmas intereses / grāmatvedība | 10 gadi (grāmatvedības prasība), pēc konta dzēšanas — **anonimizēti** |
| Audit žurnāls (OPS-001) | Iedzīvotājs / vadītājs | darbība, laiks, vecā/jaunā vērtība | Leģitīmas intereses (drošība) | Nemainīgs, ≥ 3 gadi |

## 2. Datu subjekta tiesības

### Piekļuve un pārnesamība (Art. 15, 20)
`GET /gdpr/export/{subject_id}` — atgriež visus subjekta datus strukturētā JSON
formātā (konts, dzīvokļu piesaiste, iesniegtie rādījumi). Skatīt
[app/gdpr.py](../app/gdpr.py).

### Dzēšana / anonimizācija (Art. 17)
`POST /gdpr/erase/{subject_id}` — dzēš kontu un dzīvokļu piesaisti, bet
skaitītāju rādījumus **anonimizē** (`submitted_by_id` → `NULL`), jo tie ir
nepieciešami norēķiniem un grāmatvedībai (leģitīmas intereses). Darbība tiek
ierakstīta audit žurnālā.

## 3. Piekļuves kontrole (multi-tenant)

- Iedzīvotājs var pieprasīt **tikai savus** datus.
- Vadītājs (`MANAGER`) — tikai sava nomnieka (organizācijas) subjektus ar
  juridisku pamatu.
- `SUPERADMIN` — globāli (platformas administrēšanai).

Pārbaudi īsteno `authorize_subject_access` ([app/gdpr.py](../app/gdpr.py)).

## 4. Retencijas mehānisms

Rādījumu glabāšana atbilst grāmatvedības prasībām (10 gadi). Konta dzēšana
neizdzēš vēsturiskos rādījumus, bet noņem to piesaisti personai (anonimizācija).
Audit žurnāls ir append-only un netiek dzēsts.
