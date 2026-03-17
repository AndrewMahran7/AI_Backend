# Mock Hardware Database (PCB Components)

This database simulates a realistic subset of hardware components that might exist in an enterprise system (e.g., SAP PLM). It is designed for demoing AI-powered querying, retrieval, and reasoning over engineering data.

Each record represents a **component datasheet**, including structured metadata and full-text technical descriptions.

---

# Overview

Total Records: 11  
Categories:
- Voltage Regulators (2)
- Microcontrollers (2)
- MOSFETs (2)
- Sensors (2)
- Capacitors (1)
- Communication Modules (2)

All records are ingested through the backend pipeline:
- Chunking
- Embedding (vector search)
- Summarization
- Indexed for semantic retrieval

---

# Schema (Conceptual)

Each record contains:

## Record
- `id` (UUID)
- `title`
- `type` = "component_datasheet"
- `source` = "mock_sap"
- `metadata` (JSONB)
- `content` (full datasheet text)

## Derived Data
- `record_chunks` → embedded text chunks for retrieval
- `record_summaries` → structured summaries (keywords, entities, etc.)

---

# Categories and Components

---

## 1. Voltage Regulators

### VRG8410 – 3.3V / 5A Buck Converter
- Topology: Synchronous Buck
- Input: 4.5V – 28V
- Output: 0.8V – 5.5V (3.3V default)
- Current: 5A
- Efficiency: 95%
- Notable:
  - Integrated MOSFETs
  - Adjustable switching frequency
  - Industrial-grade applications

---

### BCV2201 – 12V Boost Converter
- Topology: Boost
- Input: 2.7V – 5.5V
- Output: up to 12V
- Current: 2A (at 5V input)
- Notable:
  - Integrated MOSFET
  - Designed for portable/IoT systems
  - High duty cycle constraints

---

## 2. Microcontrollers

### ACM32F407 – Cortex-M4 (High Performance)
- Clock: 168 MHz
- Flash: 1 MB
- SRAM: 256 KB
- Interfaces: USB, CAN, SPI, UART, I2C
- Notable:
  - DSP + FPU
  - Industrial applications
  - No Ethernet (requires external chip)

---

### ACM32L051 – Cortex-M0+ (Low Power)
- Clock: 32 MHz
- Flash: 64 KB
- SRAM: 8 KB
- Ultra-low power modes
- Notable:
  - Battery-powered systems
  - Limited memory
  - No USB or CAN

---

## 3. MOSFETs

### PNF3007 – N-Channel Power MOSFET
- Voltage: 30V
- Current: 60A
- RDS(on): ~3 mΩ
- Notable:
  - High current switching
  - Logic-level gate drive
  - Thermal constraints at high load

---

### PPF4435 – P-Channel MOSFET
- Voltage: -30V
- Current: -4.3A
- RDS(on): ~35 mΩ
- Notable:
  - High-side switching
  - Low gate threshold
  - Limited thermal capacity (SOT-23)

---

## 4. Sensors

### THP310 – Temp + Humidity Sensor
- Accuracy: ±0.1°C, ±1.5% RH
- Interface: I2C
- Power: ultra-low (µA range)
- Notable:
  - Precision monitoring
  - Environmental systems

---

### IMU6050A – 6-Axis IMU
- Accelerometer + Gyroscope
- Interface: SPI / I2C
- Features:
  - Digital Motion Processor (DMP)
- Notable:
  - Robotics, drones
  - Requires calibration

---

## 5. Capacitor

### GRM21BC71E106KA – 10µF MLCC
- Voltage: 25V
- Dielectric: X7R
- Notable:
  - DC bias derating (~55%)
  - Used in power stability
  - High-frequency decoupling

---

## 6. Communication Modules

### WIZ5500 – Ethernet Controller
- Interface: SPI
- Built-in TCP/IP stack
- 8 sockets
- Notable:
  - Offloads networking from MCU
  - No TLS/SSL
  - Used with low-power MCUs

---

### RFM95W – LoRa Transceiver
- Frequency: 868 MHz
- Range: up to 15 km
- Sensitivity: -148 dBm
- Notable:
  - Ultra long-range
  - Very low data rate
  - Duty cycle limitations

---

# Relationships (Implicit)

The dataset is designed to support reasoning across components:

### Power Systems
- Regulators + Capacitors + MOSFETs

### Embedded Systems
- Microcontrollers + Sensors + Communication

### IoT Devices
- Low-power MCU + Sensor + LoRa / Ethernet

---

# Example Queries (Demo Ready)

## Comparison
- "Compare the two voltage regulators"

## Selection
- "Which component is best for a battery-powered sensor?"

## Constraints
- "What limitations does the PNF3007 have?"

## System Design
- "What components are needed for an IoT monitoring device?"

## Communication
- "Which components support SPI?"

---

# Design Intent

This dataset is intentionally:

- **Realistic** → resembles enterprise engineering data
- **Structured + unstructured** → supports hybrid retrieval
- **Cross-related** → enables reasoning, not just lookup
- **Diverse** → covers multiple PCB domains

---

# Notes

- All data is synthetic but engineered to resemble real datasheets
- Designed for RAG (Retrieval-Augmented Generation)
- Optimized for:
  - semantic search
  - structured answers
  - engineering reasoning

---

# Next Steps (Production)

In a real deployment:
- Data would come from SAP / PLM systems
- Records would be continuously updated
- Permissions and access control would be enforced
- Larger datasets would be indexed with the same pipeline