# Protocolo Bluetooth do Junctek KG-F (módulo BTG166)

Engenharia reversa feita observando as notificações BLE do monitor. Testado com **KG140F + BTG166**.

## Conexão

| Item | Valor |
|---|---|
| Nome Bluetooth | `BTG166` (pode variar por modelo/módulo) |
| Serviço | `0000ffe0-0000-1000-8000-00805f9b34fb` |
| Característica (notify) | `0000ffe1-0000-1000-8000-00805f9b34fb` |
| Conexões simultâneas | **1** (o app do celular e o ESP32 não conectam ao mesmo tempo) |

Basta assinar as notificações do `FFE1`; o monitor começa a enviar sozinho, sem precisar mandar nenhum comando.

## Formato das mensagens

```
BB  <dígitos BCD> <etiqueta>  <dígitos BCD> <etiqueta>  ...  EE
```

- `0xBB` = início, `0xEE` = fim. Uma mensagem pode chegar quebrada em mais de uma notificação, por isso o leitor guarda o estado entre elas.
- **Dígitos BCD:** cada byte cujos dois "nibbles" são de 0 a 9 representa dois dígitos decimais. Ex.: `0x12 0x34` = `"1234"`.
- **Etiqueta:** o primeiro byte que **não** é BCD (nibble ≥ A) fecha o número anterior e diz o que ele significa.
- O monitor **só envia os campos que mudaram** desde a última mensagem.

Exemplo: `BB 12 34 C0 EE` → número `1234` com etiqueta `C0` → tensão = 12,34 V.

## Etiquetas conhecidas

| Etiqueta | Campo | Conversão | Exemplo |
|---|---|---|---|
| `C0` | Tensão | ÷ 100 → V | `1234` → 12,34 V |
| `C1` | Corrente (sem sinal) | ÷ 100 → A | `523` → 5,23 A |
| `D1` | Sentido da corrente | `1` = carregando, outro = descarregando | |
| `D2` | Capacidade restante | ÷ 1000 → Ah | `25500` → 25,5 Ah |
| `D3` | Total descarregado (contador) | ÷ 1000 → Ah | sobe enquanto descarrega |
| `D4` | Total carregado (contador) | ÷ 1000 → Ah | sobe enquanto carrega |
| `D6` | Tempo restante | minutos (÷ 60 → h) | |
| `D8` | Potência (sem sinal) | ÷ 100 → W | `6470` → 64,7 W |
| `D9` | Temperatura | − 100 → °C | `125` → 25 °C |

Outras etiquetas aparecem às vezes (configurações do aparelho) e são ignoradas.

## Sentido da corrente

`C1` e `D8` vêm sempre positivos. O sentido vem de `D1`, mas como o monitor só manda o que muda, o leitor também confere pelos contadores: se `D3` (descarregado) sobe, está descarregando; se `D4` (carregado) sobe, está carregando. A corrente e a potência publicadas ficam **positivas carregando e negativas descarregando**, que é o padrão do painel de Energia do Home Assistant.
