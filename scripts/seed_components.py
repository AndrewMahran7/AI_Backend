"""Seed script – ingest realistic hardware component datasheets into the AI backend."""

import asyncio

import httpx

BASE_URL = "http://localhost:8000/api/v1/ingest"

records = [
    # ── Voltage Regulators ───────────────────────────────────────────────
    {
        "title": "VRG8410 – 3.3 V / 5 A Synchronous Buck Converter",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "VRG8410-3R3",
            "manufacturer": "NovaPower Semiconductor",
            "category": "voltage_regulator",
            "package": "QFN-20 (4x4 mm)",
            "key_specs": {
                "topology": "synchronous buck",
                "input_voltage_range": "4.5 V – 28 V",
                "output_voltage": "3.3 V (adjustable 0.8 V – 5.5 V)",
                "max_output_current": "5 A",
                "switching_frequency": "500 kHz – 2.2 MHz",
                "efficiency_peak": "95%",
                "quiescent_current": "28 µA"
            }
        },
        "content": (
            "VRG8410-3R3 – 3.3 V / 5 A Synchronous Buck Converter\n"
            "=====================================================\n\n"
            "Overview\n"
            "--------\n"
            "The VRG8410-3R3 is a high-efficiency synchronous step-down (buck) converter designed for "
            "point-of-load regulation in industrial, automotive, and embedded computing applications. "
            "It integrates high-side and low-side N-channel MOSFETs with an adaptive on-time control "
            "architecture that provides excellent transient response while maintaining a constant "
            "switching frequency under steady-state conditions. The device operates from a 4.5 V to "
            "28 V input rail and delivers up to 5 A of continuous output current at a programmable "
            "output voltage between 0.8 V and 5.5 V, set via an external resistor divider.\n\n"
            "Key Features\n"
            "------------\n"
            "- Wide input voltage range: 4.5 V to 28 V, suitable for 5 V, 12 V, and 24 V bus rails\n"
            "- Peak efficiency of 95% at 3.3 V / 3 A load, reducing thermal dissipation and eliminating "
            "the need for heat sinks in most designs\n"
            "- Programmable switching frequency from 500 kHz to 2.2 MHz via an external resistor on the "
            "RT pin, allowing designers to trade efficiency for smaller inductors at higher frequencies\n"
            "- Integrated bootstrap diode eliminates the external bootstrap capacitor\n"
            "- Ultra-low 28 µA quiescent current in pulse-frequency modulation (PFM) mode ensures "
            "battery-powered systems remain efficient at light loads\n"
            "- Internal soft-start with adjustable ramp time (1 ms to 10 ms) prevents inrush current "
            "during power sequencing\n"
            "- Cycle-by-cycle current limiting and thermal shutdown with automatic recovery provide "
            "robust fault protection\n"
            "- Output voltage accuracy of ±1% over the full operating temperature range of –40 °C to +125 °C\n\n"
            "Electrical Characteristics (Tj = 25 °C unless otherwise noted)\n"
            "--------------------------------------------------------------\n"
            "Input voltage range: 4.5 V min, 28 V max. Recommended operating input: 5 V to 24 V. "
            "Output voltage accuracy: ±1.0% (0 °C to 85 °C), ±1.5% (–40 °C to 125 °C). "
            "Reference voltage (VREF): 0.800 V typical. "
            "Feedback bias current: 50 nA typical, 200 nA maximum. "
            "High-side MOSFET RDS(on): 42 mΩ typical at VIN = 12 V, IOUT = 5 A. "
            "Low-side MOSFET RDS(on): 28 mΩ typical. "
            "Switching frequency range: 500 kHz to 2.2 MHz (programmable). "
            "Peak efficiency: 95% at VIN = 12 V, VOUT = 3.3 V, IOUT = 3 A, fSW = 600 kHz. "
            "Quiescent current (PFM mode): 28 µA typical. "
            "Shutdown current: 1.2 µA typical. "
            "Output ripple voltage: 10 mV peak-to-peak typical at 3.3 V / 5 A with recommended LC filter. "
            "Thermal shutdown threshold: 165 °C with 15 °C hysteresis.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Industrial automation PLCs and I/O modules powered from 24 V backplanes\n"
            "- Embedded single-board computers requiring 3.3 V and 1.8 V core rails from a 5 V USB-C input\n"
            "- Telecom small-cell base stations with 12 V intermediate bus\n"
            "- Battery-powered instrumentation where light-load efficiency is critical to extend run time\n"
            "- Automotive body control modules operating from the 12 V battery bus\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The VRG8410 is not recommended for output voltages below 0.8 V; for sub-0.8 V rails, "
            "consider a dedicated low-voltage converter with a 0.6 V reference. The device requires a "
            "minimum output capacitance of 44 µF ceramics (22 µF × 2, X5R or X7R) to maintain loop "
            "stability at full load. At switching frequencies above 1.5 MHz, efficiency drops "
            "approximately 3–4 percentage points due to increased gate-drive losses, so designers should "
            "benchmark carefully when optimizing for board area at high frequency. The QFN-20 exposed pad "
            "must be soldered to a ground plane with at least four thermal vias to keep junction "
            "temperature within the rated limit at sustained 5 A output."
        ),
    },
    {
        "title": "BCV2201 – 12 V / 2 A Boost Converter with Integrated MOSFET",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "BCV2201-12",
            "manufacturer": "NovaPower Semiconductor",
            "category": "voltage_regulator",
            "package": "TSOT-23-6",
            "key_specs": {
                "topology": "boost",
                "input_voltage_range": "2.7 V – 5.5 V",
                "output_voltage": "12 V (adjustable 5 V – 15 V)",
                "max_output_current": "2 A (at VIN = 5 V)",
                "switching_frequency": "1.2 MHz fixed",
                "efficiency_peak": "92%",
                "quiescent_current": "45 µA"
            }
        },
        "content": (
            "BCV2201-12 – 12 V / 2 A Boost Converter with Integrated MOSFET\n"
            "===============================================================\n\n"
            "Overview\n"
            "--------\n"
            "The BCV2201-12 is a current-mode step-up (boost) DC-DC converter that generates a regulated "
            "12 V output from input supplies as low as 2.7 V. An integrated 120 mΩ N-channel MOSFET "
            "supports peak switch currents up to 4 A, enabling up to 2 A continuous output current when "
            "operating from a 5 V bus. The fixed 1.2 MHz switching frequency allows the use of small, "
            "low-profile inductors (2.2 µH to 4.7 µH) and ceramic output capacitors, making it well "
            "suited for space-constrained wearable, IoT, and portable instrument designs.\n\n"
            "Key Features\n"
            "------------\n"
            "- Input voltage range: 2.7 V to 5.5 V, compatible with single-cell Li-ion (3.0 V–4.2 V) "
            "and USB 5 V sources\n"
            "- Adjustable output from 5 V to 15 V via external resistor divider with 1.25 V reference\n"
            "- Integrated 120 mΩ N-channel power MOSFET with 4 A peak current capability\n"
            "- Fixed 1.2 MHz switching frequency reduces inductor and capacitor size\n"
            "- Current-mode control with slope compensation ensures stable operation across all load "
            "conditions and duty cycles up to 90%\n"
            "- Internal soft-start limits inrush current to protect upstream LDOs and battery packs\n"
            "- Programmable under-voltage lockout (UVLO) via the EN/UVLO pin\n"
            "- Thermal shutdown at 150 °C and cycle-by-cycle over-current protection\n"
            "- Available in a tiny TSOT-23-6 package for compact PCB layouts\n\n"
            "Electrical Characteristics (Tj = 25 °C)\n"
            "----------------------------------------\n"
            "Input voltage: 2.7 V min, 5.5 V max. "
            "Reference voltage: 1.250 V ±1.5%. "
            "Feedback pin bias current: 10 nA typical. "
            "Switching frequency: 1.2 MHz ±10%. "
            "Internal MOSFET RDS(on): 120 mΩ at VGS = 5 V. "
            "Peak switch current limit: 4.0 A typical, 4.5 A max. "
            "Quiescent current (switching, no load): 45 µA typical. "
            "Shutdown current: 0.5 µA typical. "
            "Peak efficiency: 92% at VIN = 5 V, VOUT = 12 V, IOUT = 500 mA. "
            "Line regulation: 0.05%/V. Load regulation: 0.3%/A. "
            "Maximum duty cycle: 90%. "
            "Operating temperature range: –40 °C to +85 °C.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Driving white-LED backlights in portable medical displays requiring 12 V rails\n"
            "- Powering MEMS microphone arrays and sensor analog front-ends needing low-noise 12 V bias\n"
            "- Generating gate-drive supply for external MOSFETs in motor controllers\n"
            "- USB-powered test fixtures that require a 12 V rail for relay coils or solenoids\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "Boost converters cannot regulate the output below the input voltage; if VIN exceeds the "
            "programmed 12 V target, the output will rise to VIN minus the diode drop. Applications "
            "requiring true shutdown isolation should place a load switch on the output. The maximum "
            "achievable output current decreases sharply when VIN drops toward the 2.7 V minimum due "
            "to the duty-cycle limit; at VIN = 3.0 V and VOUT = 12 V the practical maximum output "
            "current is approximately 400 mA. A Schottky diode rated for at least 15 V / 3 A is "
            "required at the switch node; do not substitute a standard silicon diode, as the forward "
            "voltage drop degrades efficiency by 5–8 percentage points."
        ),
    },

    # ── Microcontrollers ─────────────────────────────────────────────────
    {
        "title": "ACM32F407 – ARM Cortex-M4 MCU, 168 MHz, 1 MB Flash, Industrial Grade",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "ACM32F407VGT6",
            "manufacturer": "Arctos Microelectronics",
            "category": "microcontroller",
            "package": "LQFP-100 (14x14 mm)",
            "key_specs": {
                "core": "ARM Cortex-M4F",
                "max_clock": "168 MHz",
                "flash": "1 MB",
                "sram": "256 KB",
                "adc": "3× 12-bit, 2.4 MSPS",
                "communication": "USB 2.0 FS, CAN 2.0B, 3×SPI, 4×UART, 2×I2C",
                "operating_voltage": "1.8 V – 3.6 V",
                "temperature_range": "-40 °C to +105 °C"
            }
        },
        "content": (
            "ACM32F407VGT6 – ARM Cortex-M4 MCU, 168 MHz, 1 MB Flash\n"
            "=======================================================\n\n"
            "Overview\n"
            "--------\n"
            "The ACM32F407VGT6 is a high-performance 32-bit microcontroller built on the ARM Cortex-M4F "
            "core with a single-precision floating-point unit (FPU) and DSP instruction extensions. "
            "Clocked at up to 168 MHz, it pairs 1 MB of embedded flash with 256 KB of SRAM, making it "
            "suitable for compute-intensive industrial control, motor drive, and real-time signal "
            "processing applications. The device integrates a rich peripheral set, including three "
            "12-bit ADCs, USB 2.0 Full-Speed, CAN 2.0B, and multiple serial interfaces, all accessible "
            "through an optimized multi-layer AHB bus matrix that allows simultaneous DMA and CPU access "
            "without stalling.\n\n"
            "Key Features\n"
            "------------\n"
            "- ARM Cortex-M4F core at 168 MHz with hardware FPU and DSP extensions, delivering up to "
            "210 DMIPS and 562 CoreMark\n"
            "- 1 MB dual-bank flash with 0 wait-state access via the ART Accelerator cache\n"
            "- 256 KB SRAM partitioned as 192 KB main + 64 KB CCM (core-coupled memory) for "
            "deterministic interrupt handling\n"
            "- Three independent 12-bit ADCs (2.4 MSPS each) with DMA, supporting simultaneous triple "
            "interleaved sampling at 7.2 MSPS combined\n"
            "- Two 12-bit DAC channels for analog signal generation\n"
            "- USB 2.0 Full-Speed OTG with integrated PHY\n"
            "- CAN 2.0B controller with 28 filter banks, ISO 11898 compliant\n"
            "- Three SPI interfaces (up to 42 Mbit/s), four UART/USART, two I2C, SDIO\n"
            "- 16-channel DMA controller with FIFO and burst transfer support\n"
            "- Advanced motor-control timers with complementary PWM, dead-time insertion, and "
            "break inputs for BLDC and FOC algorithms\n"
            "- Hardware CRC-32 calculation unit and true random-number generator (TRNG)\n"
            "- 1.8 V to 3.6 V supply with integrated voltage regulator; separate VDDA for analog accuracy\n"
            "- Industrial temperature range: –40 °C to +105 °C\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "Supply voltage (VDD): 1.8 V min, 3.6 V max; recommended 3.3 V ±5%. "
            "Analog supply (VDDA): 1.8 V to 3.6 V, must be ≥ VDD. "
            "Core current at 168 MHz, all peripherals off: 38 mA typical. "
            "Stop mode current (all clocks off, SRAM retained): 12 µA typical. "
            "Standby mode current (RTC running): 2.2 µA typical. "
            "ADC DNL: ±0.8 LSB typical. ADC INL: ±1.5 LSB typical. "
            "Flash endurance: 10 000 program/erase cycles minimum. "
            "Data retention: 20 years at 85 °C. "
            "GPIO output drive: 8 mA per pin (high-speed mode), 25 mA absolute max.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Industrial servo drives and field-oriented control (FOC) of BLDC/PMSM motors\n"
            "- Programmable logic controllers (PLCs) and remote I/O modules in factory automation\n"
            "- Handheld test and measurement instruments with colour TFT displays\n"
            "- Building management systems: HVAC controllers, access panels, energy meters\n"
            "- UAV flight controllers requiring real-time sensor fusion (IMU + barometer + GPS)\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The ACM32F407 does not include an Ethernet MAC; designs requiring wired Ethernet should "
            "consider the ACM32F427 variant or add an external SPI-to-Ethernet bridge such as the "
            "WIZ5500. The USB peripheral supports Full-Speed (12 Mbit/s) only; High-Speed USB requires "
            "an external ULPI PHY. Flash write latency is approximately 16 µs per half-word, which may "
            "impact deterministic loop timing if in-application programming is performed during control "
            "cycles. Maximum GPIO toggle frequency is limited to 84 MHz (HCLK/2) when using the "
            "bit-banding region."
        ),
    },
    {
        "title": "ACM32L051 – Ultra-Low-Power ARM Cortex-M0+ MCU, 32 MHz, 64 KB Flash",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "ACM32L051K8T6",
            "manufacturer": "Arctos Microelectronics",
            "category": "microcontroller",
            "package": "LQFP-32 (7x7 mm)",
            "key_specs": {
                "core": "ARM Cortex-M0+",
                "max_clock": "32 MHz",
                "flash": "64 KB",
                "sram": "8 KB",
                "adc": "1× 12-bit, 1.14 MSPS",
                "communication": "1×SPI, 2×UART, 1×I2C, 1×LPUART",
                "operating_voltage": "1.65 V – 3.6 V",
                "temperature_range": "-40 °C to +85 °C"
            }
        },
        "content": (
            "ACM32L051K8T6 – Ultra-Low-Power ARM Cortex-M0+ MCU\n"
            "===================================================\n\n"
            "Overview\n"
            "--------\n"
            "The ACM32L051K8T6 is an ultra-low-power 32-bit microcontroller targeting battery-operated "
            "and energy-harvesting applications where every microamp counts. Built on the ARM Cortex-M0+ "
            "core clocked at up to 32 MHz, it combines 64 KB of flash and 8 KB of SRAM with a "
            "comprehensive low-power peripheral set including a low-power UART (LPUART) that can "
            "operate from the 32.768 kHz LSE clock. Seven low-power modes—ranging from Sleep to "
            "Shutdown—allow designers to fine-tune the trade-off between wake-up latency and current "
            "consumption.\n\n"
            "Key Features\n"
            "------------\n"
            "- ARM Cortex-M0+ core at 32 MHz delivering 28 DMIPS, optimized 2-stage pipeline\n"
            "- 64 KB flash with dual-bank capability for live firmware updates (bank swap)\n"
            "- 8 KB SRAM fully retained in Stop mode\n"
            "- Flexible clock system: 32 MHz HSI RC, 1–24 MHz HSE crystal, 32.768 kHz LSE, "
            "and multi-speed internal RC (MSI) from 65 kHz to 4.2 MHz\n"
            "- 12-bit ADC with hardware oversampling (up to 16-bit effective resolution) and "
            "1.14 MSPS conversion rate\n"
            "- LPUART capable of operating in Stop mode to receive incoming commands and wake the MCU\n"
            "- One SPI (up to 16 Mbit/s), two USART, one I2C with SMBus/PMBus support\n"
            "- 16-bit general purpose timers (×3), one low-power timer clocked from LSE\n"
            "- Low-power comparator and internal voltage reference for threshold detection "
            "without CPU intervention\n"
            "- Supply voltage: 1.65 V to 3.6 V, enabling direct operation from a single-cell "
            "NiMH battery or a regulated 1.8 V rail\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "Supply voltage: 1.65 V min, 3.6 V max. "
            "Run-mode current at 32 MHz (all peripherals off): 3.5 mA typical (3.3 V). "
            "Low-power run at 32 kHz internal RC: 8.1 µA. "
            "Stop mode with RTC, SRAM retained: 1.1 µA typical. "
            "Standby mode, no RTC: 280 nA typical. "
            "Shutdown mode: 30 nA typical. "
            "Wake-up time from Stop (MSI 4 MHz): 3.5 µs typical. "
            "ADC DNL: ±0.6 LSB. ADC INL: ±1.2 LSB at 12-bit. "
            "Flash endurance: 10 000 cycles. Data retention: 30 years at 55 °C.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Wireless sensor nodes powered by coin-cell batteries (CR2032) with multi-year life\n"
            "- Smart metering sub-GHz radio front-ends requiring periodic wake, measure, transmit cycles\n"
            "- Wearable health patches streaming data over BLE (via an external BLE radio)\n"
            "- Environmental monitoring badges: temperature, humidity, air quality\n"
            "- Electronic shelf labels in retail environments\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "With only 8 KB SRAM, the ACM32L051 is not suitable for applications requiring large "
            "frame buffers, full TCP/IP stacks, or complex DSP computations. The Cortex-M0+ core "
            "lacks hardware divide and single-cycle multiply instructions, so math-heavy algorithms "
            "execute significantly slower than on an M4 core. There is no integrated USB or CAN "
            "peripheral. Maximum ADC sampling rate drops to 750 kSPS when operating below 2.0 V. "
            "The 32-pin LQFP package limits available GPIO to 26 pins, so designs requiring more "
            "than 20 external I/O lines should consider the 48-pin variant (ACM32L051C8T6)."
        ),
    },

    # ── MOSFETs ──────────────────────────────────────────────────────────
    {
        "title": "PNF3007 – 30 V N-Channel Logic-Level MOSFET",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "PNF3007-LG",
            "manufacturer": "Granite Semiconductor",
            "category": "mosfet",
            "package": "DPAK (TO-252)",
            "key_specs": {
                "channel": "N",
                "vds_max": "30 V",
                "id_continuous": "60 A",
                "rds_on": "3.8 mΩ @ VGS = 4.5 V",
                "vgs_threshold": "1.0 V – 2.0 V",
                "gate_charge_total": "38 nC",
                "pd_max": "50 W"
            }
        },
        "content": (
            "PNF3007-LG – 30 V N-Channel Logic-Level MOSFET\n"
            "===============================================\n\n"
            "Overview\n"
            "--------\n"
            "The PNF3007-LG is a 30 V N-channel enhancement-mode MOSFET optimized for logic-level "
            "gate drive in high-current switching applications. With an RDS(on) of just 3.8 mΩ at "
            "VGS = 4.5 V and continuous drain current capability of 60 A, it is ideally suited for "
            "low-side switching in DC-DC converters, motor drivers, and load switches operating from "
            "battery packs or 5 V / 12 V rails. The device is housed in a thermally efficient DPAK "
            "(TO-252) package with an exposed drain tab for direct PCB heat-sinking.\n\n"
            "Key Features\n"
            "------------\n"
            "- Ultra-low RDS(on): 3.8 mΩ maximum at VGS = 4.5 V, 5.5 mΩ maximum at VGS = 2.5 V\n"
            "- 60 A continuous drain current (TC = 25 °C), 180 A pulsed (100 µs)\n"
            "- Logic-level gate threshold: 1.0 V to 2.0 V, allowing direct drive from 3.3 V "
            "MCU GPIO pins\n"
            "- Low total gate charge (38 nC at VDS = 15 V, VGS = 4.5 V) enables high-frequency "
            "switching with minimal gate driver loss\n"
            "- Fast switching: tRISE = 8 ns, tFALL = 6 ns typical at ID = 30 A\n"
            "- Integrated ESD protection: HBM 2 kV on all pins\n"
            "- 100% UIL tested and RG characterized at production\n"
            "- Moisture sensitivity level (MSL): 1, no dry-pack required\n\n"
            "Electrical Characteristics (TC = 25 °C)\n"
            "---------------------------------------\n"
            "BVDSS: 30 V minimum at ID = 250 µA, VGS = 0 V. "
            "VGS(th): 1.0 V min, 2.0 V max at VDS = VGS, ID = 250 µA. "
            "IDSS (drain leakage): 1 µA max at VDS = 30 V, VGS = 0 V. "
            "IGSS (gate leakage): ±100 nA at VGS = ±20 V. "
            "RDS(on) at VGS = 10 V: 2.9 mΩ typical, 3.2 mΩ max. "
            "RDS(on) at VGS = 4.5 V: 3.3 mΩ typical, 3.8 mΩ max. "
            "RDS(on) at VGS = 2.5 V: 4.8 mΩ typical, 5.5 mΩ max. "
            "Total gate charge (QG): 38 nC at VDS = 15 V, VGS = 4.5 V. "
            "Gate-drain charge (QGD): 6.2 nC. "
            "Input capacitance (CISS): 3500 pF at VDS = 15 V, f = 1 MHz. "
            "Output capacitance (COSS): 1200 pF. Reverse transfer capacitance (CRSS): 350 pF. "
            "Body diode forward voltage (VSD): 0.75 V at IS = 30 A. "
            "Body diode reverse recovery time (trr): 22 ns. "
            "Maximum junction temperature: 150 °C. "
            "Thermal resistance (junction-to-case): 2.5 °C/W.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Synchronous rectification in 12 V to 3.3 V / 5 V buck converters\n"
            "- Low-side switch for brushed DC motor drivers (up to 30 V bus)\n"
            "- Electronic fuse / load-switch circuits requiring low insertion loss\n"
            "- LED driver circuits where PWM dimming at > 100 kHz is needed\n"
            "- Battery pack protection and charge-path switching\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "Maximum VGS is ±20 V; exceeding this rating even transiently will degrade the gate "
            "oxide and lead to parametric shift or failure. When driving from 3.3 V logic, the "
            "RDS(on) increases to approximately 4.8 mΩ (VGS = 2.5 V range), which may need to "
            "be accounted for in thermal calculations at high continuous currents. At ambient "
            "temperatures above 80 °C, the continuous drain current must be de-rated per the "
            "SOA chart in the full datasheet. The DPAK package has a maximum board-level power "
            "dissipation of approximately 2.5 W without additional copper area; for sustained "
            "high-current operation, at least 2 cm² of 2 oz copper under the drain tab is recommended."
        ),
    },
    {
        "title": "PPF4435 – –30 V P-Channel MOSFET for Load Switching",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "PPF4435-LS",
            "manufacturer": "Granite Semiconductor",
            "category": "mosfet",
            "package": "SOT-23-3",
            "key_specs": {
                "channel": "P",
                "vds_max": "-30 V",
                "id_continuous": "-4.3 A",
                "rds_on": "35 mΩ @ VGS = -4.5 V",
                "vgs_threshold": "-0.6 V to -1.4 V",
                "gate_charge_total": "7.2 nC",
                "pd_max": "1.4 W"
            }
        },
        "content": (
            "PPF4435-LS – –30 V P-Channel MOSFET for Load Switching\n"
            "======================================================\n\n"
            "Overview\n"
            "--------\n"
            "The PPF4435-LS is a –30 V P-channel enhancement-mode MOSFET designed for high-side load "
            "switching, reverse-polarity protection, and power-path management in portable and "
            "battery-powered electronics. Its low gate threshold (–0.6 V to –1.4 V) allows direct "
            "control from microcontroller GPIO pins without a dedicated gate driver. Packaged in the "
            "industry-standard SOT-23-3 footprint, it occupies minimal board area while supporting "
            "continuous drain currents up to –4.3 A.\n\n"
            "Key Features\n"
            "------------\n"
            "- VDS: –30 V, suitable for 5 V to 24 V rail switching\n"
            "- RDS(on): 35 mΩ at VGS = –4.5 V, keeping conduction losses below 650 mW at 4 A\n"
            "- Low gate threshold: –0.6 V to –1.4 V, compatible with 3.3 V MCU drive levels\n"
            "- Total gate charge: 7.2 nC, enabling fast transitions with minimal driver current\n"
            "- Continuous drain current: –4.3 A at TA = 25 °C\n"
            "- Small SOT-23-3 package (2.9 mm × 1.6 mm × 1.2 mm)\n"
            "- ESD rating: HBM 4 kV, CDM 1.5 kV\n\n"
            "Electrical Characteristics (TA = 25 °C)\n"
            "---------------------------------------\n"
            "BVDSS: –30 V min at ID = –250 µA, VGS = 0 V. "
            "VGS(th): –0.6 V min, –1.4 V max at VDS = VGS, ID = –250 µA. "
            "IDSS: –1 µA max at VDS = –30 V, VGS = 0 V. "
            "RDS(on) at VGS = –10 V: 28 mΩ typical, 35 mΩ max. "
            "RDS(on) at VGS = –4.5 V: 35 mΩ typical, 45 mΩ max. "
            "RDS(on) at VGS = –2.5 V: 55 mΩ typical, 75 mΩ max. "
            "Total gate charge: 7.2 nC at VDS = –15 V, VGS = –4.5 V. "
            "CISS: 620 pF. COSS: 180 pF. CRSS: 95 pF. "
            "Body diode VSD: 0.85 V at IS = –1 A. "
            "Rise time: 12 ns. Fall time: 18 ns at ID = –2 A. "
            "Thermal resistance (junction-to-ambient): 90 °C/W.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- High-side load switches for USB peripherals and smart-home actuators\n"
            "- Reverse-polarity protection on battery input lines\n"
            "- Power-path ORing between battery and wall-adapter supplies\n"
            "- Discrete power multiplexers in dual-rail embedded systems\n"
            "- Low-loss enable/disable switch for sub-circuits during sleep modes\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The SOT-23-3 package limits power dissipation to 1.4 W at TA = 25 °C without forced "
            "air cooling; continuous currents above 3 A require careful thermal analysis. When VGS "
            "is in the –2.0 V to –2.5 V range, RDS(on) rises significantly, so a pull-down to "
            "battery voltage (not just 3.3 V logic level) is recommended for the lowest drop at "
            "currents above 2 A. The body diode forward recovery time is approximately 40 ns, "
            "which may cause brief voltage spikes during inductive load switching if no freewheeling "
            "path is provided."
        ),
    },

    # ── Sensors ──────────────────────────────────────────────────────────
    {
        "title": "THP310 – High-Accuracy Digital Temperature & Humidity Sensor (I2C)",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "THP310-DI",
            "manufacturer": "Meridian Sensor Technologies",
            "category": "sensor",
            "package": "DFN-6 (2x2 mm)",
            "key_specs": {
                "measured_parameters": "temperature, relative humidity",
                "temperature_accuracy": "±0.1 °C (0 to 60 °C)",
                "humidity_accuracy": "±1.5 %RH (20–80 %RH)",
                "interface": "I2C up to 1 MHz",
                "supply_voltage": "1.8 V – 3.6 V",
                "current_draw": "3.4 µA average at 1 Hz"
            }
        },
        "content": (
            "THP310-DI – High-Accuracy Digital Temperature & Humidity Sensor\n"
            "===============================================================\n\n"
            "Overview\n"
            "--------\n"
            "The THP310-DI is a factory-calibrated, fully digital temperature and relative humidity "
            "sensor designed for precision environmental monitoring. It combines a bandgap temperature "
            "sensing element with a capacitive polymer humidity transducer and a 16-bit sigma-delta "
            "ADC on a single CMOS die, outputting linearized and temperature-compensated readings over "
            "a standard I2C bus. With ±0.1 °C temperature accuracy and ±1.5 %RH humidity accuracy "
            "across the most commonly used measurement ranges, it meets the stringent requirements of "
            "pharmaceutical cold-chain monitoring, HVAC control loops, and semiconductor cleanroom "
            "environmental tracking.\n\n"
            "Key Features\n"
            "------------\n"
            "- Temperature accuracy: ±0.1 °C over 0 °C to 60 °C; ±0.2 °C over –40 °C to +125 °C\n"
            "- Humidity accuracy: ±1.5 %RH over 20 %RH to 80 %RH, ±2.5 %RH over full 0–100 %RH range\n"
            "- 16-bit output resolution: 0.01 °C and 0.01 %RH per LSB\n"
            "- I2C interface up to 1 MHz (Fast-mode Plus) with two selectable addresses\n"
            "- Programmable measurement rate: single-shot or periodic from 0.5 Hz to 10 Hz\n"
            "- Integrated 8-bit CRC on every data transfer for communication integrity\n"
            "- Alert pin with configurable high/low thresholds for both temperature and humidity\n"
            "- Supply: 1.8 V to 3.6 V, 3.4 µA average at 1 Hz periodic mode, 0.1 µA in sleep\n"
            "- Factory-calibrated — no user calibration required; NIST-traceable production process\n"
            "- Tiny DFN-6 package (2 mm × 2 mm × 0.75 mm)\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "VDD: 1.8 V min, 3.6 V max. "
            "Current (single-shot measurement, high repeatability): 600 µA peak for 15 ms. "
            "Average current at 1 Hz periodic: 3.4 µA. "
            "Idle / sleep current: 0.1 µA typical. "
            "Temperature sensor range: –40 °C to +125 °C. "
            "Humidity sensor range: 0 %RH to 100 %RH (non-condensing). "
            "Temperature response time (τ63): 5 seconds in still air. "
            "Humidity response time (τ63): 8 seconds at 25 °C, 1 m/s airflow. "
            "Long-term drift: < 0.03 °C/year, < 0.25 %RH/year. "
            "I2C addresses: 0x44 (default), 0x45 (ADDR pin high).\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Pharmaceutical and vaccine cold-chain data loggers\n"
            "- HVAC zone controllers and smart thermostats\n"
            "- Server-room and data-centre environmental monitoring panels\n"
            "- Agricultural greenhouse automation\n"
            "- Consumer weather stations and indoor air-quality hubs\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The humidity sensor is rated for non-condensing environments only; prolonged exposure "
            "to liquid water or dew formation on the sensing surface can cause temporary offset shifts "
            "of up to 3 %RH, recovering within 24 hours after drying. Chemical contaminants such as "
            "volatile organic compounds (VOCs) above 10 ppm may degrade the polymer dielectric over "
            "months of exposure; a PTFE membrane filter cap is recommended for industrial deployments. "
            "The sensor should not be placed directly above heat-generating components (regulators, "
            "power MOSFETs) on the PCB, as radiated and conducted heat will bias the temperature "
            "reading. Minimum recommended keep-out from heat sources is 5 mm with a thermal relief "
            "routing pattern."
        ),
    },
    {
        "title": "IMU6050A – 6-Axis MEMS Inertial Measurement Unit (Accel + Gyro)",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "IMU6050A-QN",
            "manufacturer": "Meridian Sensor Technologies",
            "category": "sensor",
            "package": "QFN-24 (4x4 mm)",
            "key_specs": {
                "axes": "3-axis accelerometer + 3-axis gyroscope",
                "accel_range": "±2 / ±4 / ±8 / ±16 g",
                "gyro_range": "±250 / ±500 / ±1000 / ±2000 °/s",
                "adc_resolution": "16-bit",
                "interface": "SPI (10 MHz) / I2C (400 kHz)",
                "supply_voltage": "1.71 V – 3.6 V",
                "current_draw": "3.2 mA (accel + gyro active)"
            }
        },
        "content": (
            "IMU6050A-QN – 6-Axis MEMS Inertial Measurement Unit\n"
            "====================================================\n\n"
            "Overview\n"
            "--------\n"
            "The IMU6050A-QN is a six-degree-of-freedom (6-DOF) inertial measurement unit combining a "
            "3-axis MEMS accelerometer and a 3-axis MEMS gyroscope with a dedicated Digital Motion "
            "Processor (DMP) in a compact QFN-24 package. The on-chip DMP can offload sensor-fusion "
            "algorithms from the host MCU, computing quaternion orientation, step counting, and tap "
            "detection internally. Data is available via SPI (up to 10 MHz) or I2C (up to 400 kHz), "
            "with configurable data-ready and FIFO-watermark interrupts.\n\n"
            "Key Features\n"
            "------------\n"
            "- 3-axis accelerometer: selectable full-scale ±2 g, ±4 g, ±8 g, ±16 g, "
            "16-bit output, noise density 100 µg/√Hz at ±2 g\n"
            "- 3-axis gyroscope: selectable ±250, ±500, ±1000, ±2000 °/s, "
            "16-bit output, noise density 0.005 °/s/√Hz at ±250 °/s\n"
            "- Integrated Digital Motion Processor for sensor fusion, free-fall detection, "
            "zero-motion detection, and pedometer functions\n"
            "- 1 KB FIFO buffer prevents data loss during host processor sleep intervals\n"
            "- Programmable digital low-pass filters (DLPF) with bandwidth from 5 Hz to 260 Hz\n"
            "- Configurable output data rate (ODR) up to 8 kHz for accelerometer, 32 kHz for gyroscope "
            "in SPI-only mode\n"
            "- Self-test capability per MEMS industry standards for production-line verification\n"
            "- Supply: 1.71 V to 3.6 V; separate VDDIO pin for flexible logic-level interfacing "
            "(1.71 V to VDD)\n"
            "- Operating temperature: –40 °C to +85 °C\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "VDD: 1.71 V min, 3.6 V max. "
            "Current (accel + gyro, ODR 1 kHz): 3.2 mA typical. "
            "Accel-only mode: 450 µA. Gyro-only mode: 2.8 mA. "
            "Sleep mode current: 6 µA with wake-on-motion enabled. "
            "Accelerometer zero-g offset: ±30 mg typical. "
            "Gyroscope zero-rate offset: ±3 °/s typical (calibrated via DMP). "
            "Accelerometer sensitivity: 16384 LSB/g at ±2 g. "
            "Gyroscope sensitivity: 131 LSB/(°/s) at ±250 °/s. "
            "Cross-axis sensitivity: ±1% typical. "
            "SPI clock: up to 10 MHz. I2C: standard (100 kHz) and fast (400 kHz) modes. "
            "Interrupt latency from event to INT pin assertion: < 3.5 µs.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Drone and UAV attitude estimation and stabilization\n"
            "- Robotic joint monitoring and dead-reckoning navigation\n"
            "- Wearable fitness trackers: step counting, gesture recognition\n"
            "- Image stabilization (OIS) in camera gimbals\n"
            "- Vibration monitoring on industrial rotating machinery\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The MEMS gyroscope exhibits a turn-on bias drift of up to ±5 °/s that must be "
            "compensated by a stationary calibration routine at each power-on or via the DMP's "
            "auto-calibration mode (requires 8 seconds of stillness). Accelerometer bandwidth is "
            "limited to 1.13 kHz with the internal DLPF enabled; applications requiring vibration "
            "analysis above 1 kHz should bypass the DLPF and apply external filtering. The 1 KB FIFO "
            "fills in approximately 42 ms at a 4 kHz ODR with 6-axis data; the host must read the "
            "FIFO before overflow or data will be lost. The I2C address is fixed at either 0x68 or "
            "0x69 (selected by the AD0 pin), allowing only two devices per I2C bus without a multiplexer."
        ),
    },

    # ── Capacitor ────────────────────────────────────────────────────────
    {
        "title": "GRM21BC71E106KA – 10 µF / 25 V X7R MLCC (0805)",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "GRM21BC71E106KA",
            "manufacturer": "Muon Capacitor Corp",
            "category": "capacitor",
            "package": "0805 (2012 metric)",
            "key_specs": {
                "capacitance": "10 µF",
                "voltage_rating": "25 V",
                "dielectric": "X7R",
                "tolerance": "±10%",
                "temperature_range": "-55 °C to +125 °C"
            }
        },
        "content": (
            "GRM21BC71E106KA – 10 µF / 25 V X7R Ceramic Capacitor (0805)\n"
            "============================================================\n\n"
            "Overview\n"
            "--------\n"
            "The GRM21BC71E106KA is a 10 µF multi-layer ceramic capacitor (MLCC) in the compact 0805 "
            "(2012 metric) case size, rated for 25 V DC. It uses an X7R (Class II) barium-titanate "
            "dielectric system that provides a good balance between volumetric efficiency and "
            "capacitance stability over temperature and applied voltage. This capacitor is a "
            "general-purpose workhorse for decoupling, bulk bypassing, and energy storage in power "
            "supply output stages.\n\n"
            "Key Features\n"
            "------------\n"
            "- Nominal capacitance: 10 µF ±10% (K tolerance)\n"
            "- Rated voltage: 25 V DC, 16 V AC maximum ripple\n"
            "- Dielectric: X7R — capacitance change ≤ ±15% over –55 °C to +125 °C\n"
            "- Low ESR: < 5 mΩ at 1 MHz, making it effective at decoupling high-frequency switching noise\n"
            "- Self-resonant frequency (SRF): approximately 3.5 MHz\n"
            "- 0805 package (2.0 mm × 1.25 mm × 1.25 mm) — compatible with automated pick-and-place "
            "assembly down to 0.4 mm pitch\n"
            "- RoHS compliant, halogen-free\n"
            "- Qualified to AEC-Q200 for automotive applications\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "Capacitance at 1 kHz, 1.0 Vrms, 25 °C: 10 µF ±10%. "
            "DC voltage derating: at 25 V applied bias the effective capacitance drops to approximately "
            "4.5 µF (55% loss) due to the DC bias characteristic of X7R ceramics; at 12 V it is "
            "approximately 7.0 µF (30% loss). "
            "Insulation resistance: > 10 GΩ or RC > 500 s (whichever is smaller) at 25 °C. "
            "Dissipation factor (tan δ): ≤ 2.5% at 1 kHz. "
            "ESR at 1 MHz: < 5 mΩ. "
            "Rated ripple current: 3 A rms at 100 kHz, subject to temperature derating. "
            "Temperature coefficient of capacitance (TCC): ±15% max from –55 °C to +125 °C. "
            "Dielectric withstanding voltage: 62.5 V for 5 seconds (2.5× rated). "
            "Operating temperature range: –55 °C to +125 °C.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Output capacitor on buck converter stages (VRG8410, etc.) — place two in parallel "
            "for 20 µF effective at low bias to ensure loop stability\n"
            "- Input decoupling on microcontroller VDD pins (ACM32F407)\n"
            "- Bulk bypass on FPGA VCCINT rails alongside smaller 100 nF ceramics\n"
            "- Energy buffer for pulsed-load wireless transmitters (LoRa, sub-GHz)\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The most critical characteristic to account for in design is the DC-bias capacitance "
            "derating. At the full 25 V rating, effective capacitance drop approaches 55%, so two "
            "capacitors in parallel may be needed to meet minimum bulk-capacitance requirements for "
            "switching-regulator stability. X7R ceramics also exhibit piezoelectric effects (acoustic "
            "noise / 'singing capacitor' phenomenon) when subjected to AC ripple at audio frequencies; "
            "if audible noise is a concern, consider using C0G capacitors for the signal path or "
            "mounting the MLCC on a flex-bonded pad. Do not exceed 62.5 V even transiently during "
            "hot-plug events — add an input TVS diode or use a higher voltage rated part."
        ),
    },

    # ── Communication Chips ──────────────────────────────────────────────
    {
        "title": "WIZ5500-SR – Hardwired TCP/IP Ethernet Controller (SPI)",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "WIZ5500-SR",
            "manufacturer": "Lattice Network Devices",
            "category": "communication",
            "package": "LQFP-48 (7x7 mm)",
            "key_specs": {
                "interface_host": "SPI up to 80 MHz",
                "ethernet": "10/100 Base-T with integrated MAC & PHY",
                "sockets": "8 simultaneous TCP/UDP",
                "buffer": "32 KB TX + 32 KB RX",
                "supply_voltage": "3.3 V",
                "current_draw": "132 mA typical (active)"
            }
        },
        "content": (
            "WIZ5500-SR – Hardwired TCP/IP Ethernet Controller\n"
            "=================================================\n\n"
            "Overview\n"
            "--------\n"
            "The WIZ5500-SR is a single-chip 10/100 Mbps Ethernet controller that integrates a full "
            "hardwired TCP/IP stack, a 10/100 Ethernet MAC, and a PHY with auto-MDIX. It offloads the "
            "entire TCP/IP processing burden from the host MCU, freeing CPU cycles for application logic "
            "and reducing firmware complexity. The host communicates with the WIZ5500 over a standard "
            "SPI bus running at up to 80 MHz, reading and writing socket registers and data buffers "
            "without any TCP/IP software stack. This makes it an ideal solution for resource-constrained "
            "microcontrollers (Cortex-M0/M0+) that lack the memory for a software stack.\n\n"
            "Key Features\n"
            "------------\n"
            "- Hardwired TCP/IP protocols: TCP, UDP, IPv4, ICMP, ARP, IGMP, PPPoE\n"
            "- 8 independent hardware sockets, each supporting TCP server, TCP client, UDP, or "
            "RAW Ethernet mode simultaneously\n"
            "- SPI host interface: up to 80 MHz clock, variable-length burst read/write with "
            "auto-incrementing address\n"
            "- Integrated 10/100 Base-T Ethernet PHY with auto-negotiation and auto-MDIX — "
            "no external magnetics required when using an RJ45 jack with integrated magnetics\n"
            "- 32 KB TX and 32 KB RX buffer, individually configurable per socket in 1/2/4/8/16 KB blocks\n"
            "- Hardware-based ARP resolution, TCP retransmission, and keep-alive timers reduce host "
            "interrupt frequency\n"
            "- Wake-on-LAN (WoL) and power-down mode (< 15 mA)\n"
            "- Supports IP fragmentation reassembly and IGMP v1/v2 for multicast\n"
            "- 3.3 V single supply; 5 V tolerant SPI pins for direct connection to 5 V MCUs\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "VDD: 3.135 V min, 3.465 V max (3.3 V ±5%). "
            "Active current (all 8 sockets, 100 Mbps link active): 132 mA typical. "
            "Power-down current: 13 mA typical with PHY disabled. "
            "SPI clock: DC to 80 MHz (mode 0 and mode 3 supported). "
            "SPI MISO output drive: 8 mA. "
            "Interrupt pin (INTn): active-low, open-drain, requires external 10 kΩ pull-up. "
            "Ethernet link-up time (auto-negotiation): < 3 seconds typical. "
            "Maximum TCP throughput (measured, single socket): 15 Mbit/s at SPI 33 MHz. "
            "RX buffer latency (from wire to SPI-readable): < 800 µs for a 64-byte frame. "
            "Operating temperature: –40 °C to +85 °C.\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- Adding Ethernet to Cortex-M0+ MCUs (e.g. ACM32L051) that lack an onboard MAC\n"
            "- Industrial Modbus TCP gateways and protocol converters\n"
            "- IoT edge devices sending MQTT telemetry to cloud brokers\n"
            "- Networked sensor hubs aggregating data from RS-485 field devices\n"
            "- Remote firmware update servers on embedded targets without a full OS\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "The WIZ5500 does not support IPv6, TLS/SSL, or DHCP server mode in hardware; "
            "DHCP client operation is supported but requires the host to execute a simple state "
            "machine using the provided socket API. Maximum simultaneous connections are limited "
            "to eight; applications requiring more must implement connection pooling in firmware. "
            "At the maximum 80 MHz SPI clock, signal integrity requires matched-length traces "
            "shorter than 10 cm and 33 Ω series termination resistors on SCLK and MOSI. The "
            "32 KB RX buffer shared among eight sockets means that high-throughput use of one "
            "socket reduces availability for others; allocate buffers according to expected traffic "
            "patterns."
        ),
    },
    {
        "title": "RFM95W-868 – LoRa Wireless Transceiver Module (868 MHz)",
        "type": "component_datasheet",
        "source": "mock_sap",
        "metadata": {
            "part_number": "RFM95W-868S2",
            "manufacturer": "Signalix Wireless",
            "category": "communication",
            "package": "SMD module (16×16 mm)",
            "key_specs": {
                "frequency": "868 MHz (EU ISM band)",
                "modulation": "LoRa (CSS) / FSK / OOK",
                "max_output_power": "+20 dBm (100 mW)",
                "sensitivity": "-148 dBm (LoRa, SF12, 125 kHz BW)",
                "interface_host": "SPI",
                "supply_voltage": "1.8 V – 3.7 V",
                "current_tx": "120 mA at +20 dBm",
                "current_rx": "10.3 mA",
                "range_los": "up to 15 km line-of-sight"
            }
        },
        "content": (
            "RFM95W-868S2 – LoRa Wireless Transceiver Module (868 MHz)\n"
            "==========================================================\n\n"
            "Overview\n"
            "--------\n"
            "The RFM95W-868S2 is a low-cost, high-performance LoRa transceiver module operating in the "
            "868 MHz European ISM band. Based on a Semtech SX1276-compatible radio IC, it supports "
            "long-range Chirp Spread Spectrum (CSS) modulation with link budgets exceeding 168 dB, "
            "enabling reliable communication at distances up to 15 km in line-of-sight conditions. "
            "The module also supports legacy FSK and OOK modulation for backward compatibility with "
            "existing sub-GHz protocols.\n\n"
            "Key Features\n"
            "------------\n"
            "- LoRa modulation with configurable spreading factor (SF6–SF12) and bandwidth "
            "(7.8 kHz to 500 kHz)\n"
            "- Receiver sensitivity: –148 dBm at SF12, 125 kHz BW — industry-leading for sub-GHz ISM\n"
            "- Transmit power: programmable from –4 dBm to +20 dBm in 1 dB steps via PA boost mode\n"
            "- Maximum RF output: +20 dBm (100 mW), meeting EU 868 MHz duty-cycle regulations\n"
            "- SPI host interface with interrupt-driven operation (DIO0–DIO5 mappable to TX Done, "
            "RX Done, FHSS channel change, etc.)\n"
            "- 256-byte FIFO for packet buffering; automatic CRC-16 generation and checking\n"
            "- Automatic frequency correction (AFC) and low-noise amplifier (LNA) with AGC\n"
            "- Supply: 1.8 V to 3.7 V — direct operation from CR123A lithium or 2× AA cells\n"
            "- Sleep current: 0.2 µA with the oscillator off\n"
            "- Operating temperature: –40 °C to +85 °C\n"
            "- Compact 16 × 16 mm SMD module with castellated edge pads for reflow soldering\n\n"
            "Electrical Characteristics\n"
            "-------------------------\n"
            "VDD: 1.8 V min, 3.7 V max. "
            "TX current at +20 dBm: 120 mA. "
            "TX current at +13 dBm: 28 mA. "
            "RX current (LoRa, LNA boost): 10.3 mA. "
            "RX current (FSK): 11.5 mA. "
            "Sleep current (RC oscillator off): 0.2 µA. "
            "Frequency range: 862 MHz to 1020 MHz (hardware capable; regulatory use at 868 MHz). "
            "LoRa bit rate: 0.018 kbps (SF12/125) to 37.5 kbps (SF6/500). "
            "FSK bit rate: up to 300 kbps. "
            "Frequency error: ±12 ppm over full temperature range. "
            "Adjacent channel selectivity: 35 dB at 200 kHz offset (LoRa, 125 kHz BW). "
            "Blocking immunity: 89 dB at 1 MHz offset. "
            "Antenna impedance: 50 Ω (SMA or U.FL connector, or trace antenna via matching network).\n\n"
            "Typical Applications\n"
            "--------------------\n"
            "- LoRaWAN Class A/C end-nodes for smart agriculture (soil moisture, weather stations)\n"
            "- Long-range asset tracking in logistics and fleet management\n"
            "- Smart-city infrastructure: parking sensors, waste-bin level monitors, street-light controllers\n"
            "- Industrial remote telemetry: tank levels, pipeline pressure, pump status\n"
            "- Building automation: wireless sub-metering, occupancy sensing\n\n"
            "Limitations and Constraints\n"
            "--------------------------\n"
            "LoRa achieves long range at the expense of data rate; at SF12 the effective throughput "
            "is only 18 bytes per second, making it unsuitable for firmware-over-the-air (FOTA) "
            "updates of large images without multi-hour transfer windows. The EU 868 MHz band imposes "
            "a 1% duty-cycle limit on most sub-bands, so a device transmitting at SF12 should not "
            "send more than one packet per 1.2 seconds. The +20 dBm PA boost mode draws 120 mA, "
            "which can cause voltage droop on coin-cell supplies — a decoupling capacitor bank "
            "(≥ 100 µF) close to the module VCC pin is required. The module does not include the "
            "LoRaWAN protocol stack; the host MCU must run a software stack such as LoRaMac-node or "
            "LMIC. Antenna matching and ground-plane design significantly affect range; a poorly "
            "matched antenna can reduce sensitivity by 10 dB or more."
        ),
    },
]


async def ingest_all(base_url: str = BASE_URL) -> None:
    """POST each record to the /ingest endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, record in enumerate(records, 1):
            payload = {
                "title": record["title"],
                "content": record["content"],
                "type": record["type"],
                "source": record["source"],
                "metadata": record.get("metadata", {}),
            }
            print(f"[{i}/{len(records)}] Ingesting: {record['title'][:70]}...")
            resp = await client.post(base_url, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"         -> record_id={data.get('record_id', 'n/a')}, "
                      f"job_id={data.get('job_id', 'n/a')}, "
                      f"status={data.get('status', 'unknown')}")
            else:
                print(f"         -> ERROR {resp.status_code}: {resp.text[:200]}")
    print(f"\nDone. Submitted {len(records)} records for ingestion.")


if __name__ == "__main__":
    asyncio.run(ingest_all())
