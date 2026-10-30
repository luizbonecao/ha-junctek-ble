# Junctek KG-F Bluetooth para Home Assistant

[![Doar com PayPal / Donate with PayPal](https://img.shields.io/badge/PayPal-Doar%20%2F%20Donate-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/donate/?business=luiz-henrique-95%40hotmail.com&no_recurring=0&currency_code=BRL)

**🇧🇷 Português** · [🇺🇸 English](#-english)

Integração para o **Home Assistant** que lê o monitor de bateria **Junctek KG-F** (KG140F, KG110F e família) **pelo Bluetooth**. É só instalar pelo **HACS**, e o Home Assistant **acha o Junctek sozinho**. Você clica em **Adicionar** e aparece um dispositivo **Junctek** com todos os sensores. Não precisa saber programar.

## O que aparece no Home Assistant

Um dispositivo **"Junctek BTG166"** em *Configurações → Dispositivos e serviços*, com:

| Sensor | Observação |
|---|---|
| **Bateria** (%) | calculada pela capacidade restante ÷ capacidade da bateria |
| **Tensão** (V) | |
| **Corrente** (A) | **positiva carregando, negativa descarregando** |
| **Potência** (W) | com sinal, igual à corrente — pronta para o painel de Energia |
| **Capacidade restante** (Ah) | |
| **Tempo restante** | estimativa do próprio Junctek |
| **Temperatura** (°C) | se o sensor de temperatura estiver ligado |
| **Estado** | Carregando / Descarregando / Parado |
| Total carregado / descarregado (Ah) | contadores (diagnóstico) |
| Conectado | se o Home Assistant está conectado ao monitor (diagnóstico) |
| Sinal Bluetooth (dBm) | desativado por padrão (diagnóstico) |

Logo depois de conectar, **Corrente**, **Potência** e **Estado** podem ficar como *desconhecido* por alguns segundos: o Junctek só informa se está carregando ou descarregando quando esse dado muda, e a integração prefere não chutar o sinal.

Os valores **continuam aparecendo depois de reiniciar** o Home Assistant: o Junctek só manda o que muda, então a integração guarda o último valor de cada sensor.

## Do que você precisa

1. Monitor **Junctek KG-F com o módulo Bluetooth** (testado: **KG140F + BTG166**).
2. **Bluetooth no Home Assistant**, de **um** destes jeitos:
   - o **Bluetooth do próprio computador** onde o Home Assistant roda; **ou**
   - um **adaptador Bluetooth USB** (pendrive) ligado nele; **ou**
   - um **ESP32 servindo de ponte Bluetooth** (Bluetooth proxy), se o computador estiver longe do Junctek ou não tiver Bluetooth. Veja [Não tenho Bluetooth](#não-tenho-bluetooth-use-um-esp32-como-ponte).
3. O Junctek a até uns **5 metros** do Bluetooth.

> ⚠️ O módulo Bluetooth do Junctek aceita **uma conexão por vez**. Feche o app do celular antes de adicionar; enquanto o Home Assistant estiver conectado, o app não conecta.

## Instalação

### 1. Instalar pelo HACS
[![Abrir no HACS / Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luizbonecao&repository=ha-junctek-ble&category=integration)

Ou manualmente:
1. Abra o **HACS** → menu ⋮ → **Repositórios personalizados**.
2. Cole `https://github.com/luizbonecao/ha-junctek-ble`, escolha o tipo **Integração** e clique em **Adicionar**.
3. Procure **Junctek KG-F Bluetooth** no HACS, clique em **Baixar**.
4. **Reinicie** o Home Assistant.

### 2. Adicionar o Junctek
- Em geral ele **aparece sozinho** em *Configurações → Dispositivos e serviços* como **"Descoberto: BTG166"**. Clique em **Adicionar**, informe a **capacidade da bateria em Ah** e pronto.
- Se não aparecer: **Adicionar integração** → **Junctek KG-F Bluetooth**, escolha o aparelho na lista (normalmente `BTG166`) e informe a capacidade.

Para mudar a capacidade depois: no cartão da integração, clique em **Configurar**.

## Não tenho Bluetooth: use um ESP32 como ponte

Um ESP32 comum (uns R$ 30) vira o "Bluetooth" do Home Assistant:

1. No app **ESPHome Device Builder**, crie um dispositivo e use o arquivo [`esphome/ponte-bluetooth-esp32.yaml`](esphome/ponte-bluetooth-esp32.yaml).
2. Preencha o Wi-Fi no `secrets.yaml` (modelo em [`esphome/secrets.yaml.example`](esphome/secrets.yaml.example)) e grave no ESP32.
3. Adicione o ESP32 no Home Assistant (ele aparece sozinho como ESPHome).
4. Deixe o ESP32 perto do Junctek. A integração acha o monitor através dele.

O ponto importante do arquivo é `bluetooth_proxy: active: true`. Ele permite que o Home Assistant **conecte** no Junctek pelo ESP32, e de bônus serve para qualquer outro aparelho Bluetooth da casa.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Nenhum aparelho Bluetooth encontrado" | Confira se o Home Assistant tem Bluetooth (*Configurações → Dispositivos → Bluetooth*) ou uma ponte ESP32 com `active: true` |
| Junctek não aparece na lista | Feche o app do celular (uma conexão por vez) e aproxime o Bluetooth do monitor |
| "Conectado" desligado | Mesmo caso acima; a integração tenta reconectar sozinha a cada 10 s |
| Porcentagem errada | Ajuste a capacidade em **Configurar** |

## Como funciona

Serviço BLE `FFE0`, característica `FFE1` com notificações; mensagens `0xBB … 0xEE` com números em BCD seguidos de uma etiqueta. Detalhes em [`docs/protocolo.md`](docs/protocolo.md).

## Apoie o projeto ☕

Até onde pesquisei, não havia outro jeito de ler o Junctek pelo Bluetooth no Home Assistant, e este projeto levou bastante trabalho. Se ele te ajudou, considere uma doação. Obrigado!

- **PayPal:** [doar pelo PayPal](https://www.paypal.com/donate/?business=luiz-henrique-95%40hotmail.com&no_recurring=0&currency_code=BRL) (ou envie para `luiz-henrique-95@hotmail.com`)

## Contribuições

Testou com outro modelo (KG110F, KG150F, KH-F…)? Abra uma *issue* contando se funcionou. Correções e melhorias são bem-vindas.

## Licença

[MIT](LICENSE) © Luiz H. Pires

> Projeto independente, **não oficial**. Junctek é marca registrada do seu dono; o nome e a logo são usados só para identificar o aparelho compatível.

---

## 🇺🇸 English

Home Assistant integration that reads the **Junctek KG-F** battery monitor (KG140F, KG110F and family) **over Bluetooth**. Install it from **HACS** and Home Assistant **finds the Junctek by itself**: click **Add** and a **Junctek** device appears with all the sensors. No programming needed.

### What you get

A **"Junctek BTG166"** device under *Settings → Devices & services* with:

| Sensor | Notes |
|---|---|
| **Battery** (%) | remaining capacity ÷ battery capacity |
| **Voltage** (V) | |
| **Current** (A) | **positive while charging, negative while discharging** |
| **Power** (W) | signed like the current, ready for the Energy dashboard |
| **Remaining capacity** (Ah) | |
| **Time left** | the monitor's own estimate |
| **Temperature** (°C) | if the temperature probe is connected |
| **State** | Charging / Discharging / Idle |
| Total charged / discharged (Ah) | counters (diagnostic) |
| Connected | whether Home Assistant is connected to the monitor (diagnostic) |
| Bluetooth signal (dBm) | disabled by default (diagnostic) |

Right after connecting, **Current**, **Power** and **State** may show *unknown* for a few seconds: the monitor only reports the direction when it changes, and the integration does not guess the sign. Values **survive a Home Assistant restart**, because the monitor only sends what changes and the integration keeps the last value of each sensor.

### Requirements

1. A **Junctek KG-F with the Bluetooth module** (tested: **KG140F + BTG166**).
2. **Bluetooth in Home Assistant**, one of:
   - the built-in Bluetooth of the machine running Home Assistant, **or**
   - a **USB Bluetooth adapter**, **or**
   - an **ESP32 acting as a Bluetooth proxy**, if the machine is far away or has no Bluetooth (see below).
3. The Junctek within about **5 m** of the Bluetooth adapter or proxy.

> ⚠️ The Junctek Bluetooth module accepts **one connection at a time**. Close the phone app before adding it; while Home Assistant is connected, the app cannot connect.

### Installation

[![Abrir no HACS / Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luizbonecao&repository=ha-junctek-ble&category=integration)

Or manually:

1. **HACS** → ⋮ menu → **Custom repositories** → paste `https://github.com/luizbonecao/ha-junctek-ble`, type **Integration** → **Add**.
2. Search **Junctek KG-F Bluetooth** in HACS → **Download** → **restart** Home Assistant.
3. It usually shows up as **"Discovered: BTG166"** in *Settings → Devices & services*. Click **Add** and enter the **battery capacity in Ah**.
   If it does not show up: **Add integration** → **Junctek KG-F Bluetooth** → pick the device (usually `BTG166`).

To change the capacity later, click **Configure** on the integration card.

### No Bluetooth? Use an ESP32 as a bridge

1. In **ESPHome Device Builder**, create a device using [`esphome/ponte-bluetooth-esp32.yaml`](esphome/ponte-bluetooth-esp32.yaml).
2. Fill in your Wi-Fi in `secrets.yaml` (template: [`esphome/secrets.yaml.example`](esphome/secrets.yaml.example)) and flash the ESP32.
3. Add the ESP32 to Home Assistant (it is discovered as ESPHome) and place it near the Junctek.

The key setting is `bluetooth_proxy: active: true`, which lets Home Assistant **connect** to the Junctek through the ESP32.

### Troubleshooting

| Symptom | What to do |
|---|---|
| "No Bluetooth devices found" | Check that Home Assistant has Bluetooth (*Settings → Devices → Bluetooth*) or an ESP32 proxy with `active: true` |
| Junctek not listed | Close the phone app (one connection at a time) and move the Bluetooth closer |
| "Connected" is off | Same as above; the integration retries every 10 s |
| Wrong percentage | Fix the capacity under **Configure** |

### How it works

BLE service `FFE0`, characteristic `FFE1` with notifications; frames `0xBB … 0xEE` with BCD numbers followed by a tag. Details in [`docs/protocolo.md`](docs/protocolo.md).

### Support the project ☕

As far as I could find, there was no other way to read the Junctek over Bluetooth in Home Assistant, and this took a lot of work. If it helped you, please consider a donation. Thank you!

- **PayPal:** [donate with PayPal](https://www.paypal.com/donate/?business=luiz-henrique-95%40hotmail.com&no_recurring=0&currency_code=BRL) (or send to `luiz-henrique-95@hotmail.com`)

### Contributing

Tested another model (KG110F, KG150F, KH-F…)? Open an *issue* and tell whether it worked. Fixes and improvements are welcome.

### License

[MIT](LICENSE) © Luiz H. Pires

> Independent, **unofficial** project. Junctek is a trademark of its owner; the name and logo are used only to identify the compatible device.
