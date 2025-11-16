"""IoT sensor data integration adapter for multimodal GraphRAG."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Represents a single sensor reading."""

    sensor_id: str
    timestamp: datetime
    value: Union[float, int, str, Dict[str, Any]]
    unit: Optional[str] = None
    quality: float = 1.0  # Quality score 0-1
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SensorDevice:
    """Represents a sensor device."""

    device_id: str
    device_type: str  # temperature, humidity, camera, microphone, accelerometer, etc.
    location: Optional[str] = None
    capabilities: List[str] = None
    status: str = "active"


class IoTSensorAdapter:
    """Adapter for integrating various IoT sensors with GraphRAG."""

    def __init__(self):
        self.connected_sensors: Dict[str, SensorDevice] = {}
        self.reading_buffer: Dict[str, List[SensorReading]] = {}

    async def register_sensor(self, device: SensorDevice, tenant_id: str) -> bool:
        """Register a new sensor device."""
        try:
            self.connected_sensors[device.device_id] = device
            self.reading_buffer[device.device_id] = []

            logger.info(f"Registered sensor {device.device_id} for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register sensor {device.device_id}: {e}")
            return False

    async def ingest_sensor_data(
        self, readings: List[SensorReading], tenant_id: str
    ) -> Dict[str, Any]:
        """Ingest sensor readings into the system."""

        processed_count = 0
        failed_count = 0

        for reading in readings:
            try:
                # Add to buffer
                if reading.sensor_id in self.reading_buffer:
                    self.reading_buffer[reading.sensor_id].append(reading)
                    processed_count += 1
                else:
                    logger.warning(f"Unknown sensor {reading.sensor_id}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"Failed to process reading from {reading.sensor_id}: {e}")
                failed_count += 1

        return {
            "processed": processed_count,
            "failed": failed_count,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_sensor_data(
        self,
        sensor_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[SensorReading]:
        """Retrieve sensor data within time range."""

        if sensor_id not in self.reading_buffer:
            return []

        readings = self.reading_buffer[sensor_id]

        # Apply time filtering
        if start_time or end_time:
            filtered_readings = []
            for reading in readings:
                if start_time and reading.timestamp < start_time:
                    continue
                if end_time and reading.timestamp > end_time:
                    continue
                filtered_readings.append(reading)
            readings = filtered_readings

        # Apply limit
        return readings[-limit:] if limit else readings

    async def detect_sensor_anomalies(
        self,
        sensor_id: str,
        tenant_id: str,
        window_size: int = 50,
        threshold: float = 2.0,
    ) -> Dict[str, Any]:
        """Detect anomalies in sensor data using statistical methods."""

        readings = await self.get_sensor_data(sensor_id, limit=window_size * 2)

        if len(readings) < window_size:
            return {"anomalies": [], "insufficient_data": True}

        # Simple statistical anomaly detection
        numeric_values = []
        for reading in readings:
            if isinstance(reading.value, (int, float)):
                numeric_values.append(reading.value)

        if not numeric_values:
            return {"anomalies": [], "non_numeric_data": True}

        # Calculate mean and std for anomaly detection
        mean_val = sum(numeric_values) / len(numeric_values)
        variance = sum((x - mean_val) ** 2 for x in numeric_values) / len(
            numeric_values
        )
        std_val = variance**0.5

        anomalies = []
        for i, reading in enumerate(readings):
            if isinstance(reading.value, (int, float)):
                z_score = abs(reading.value - mean_val) / (std_val + 1e-8)
                if z_score > threshold:
                    anomalies.append(
                        {
                            "timestamp": reading.timestamp.isoformat(),
                            "value": reading.value,
                            "z_score": z_score,
                            "severity": (
                                "high" if z_score > threshold * 1.5 else "medium"
                            ),
                        }
                    )

        return {
            "sensor_id": sensor_id,
            "anomalies": anomalies,
            "total_readings": len(readings),
            "mean": mean_val,
            "std": std_val,
            "threshold_used": threshold,
        }

    async def aggregate_sensor_data(
        self,
        sensor_ids: List[str],
        aggregation_type: str = "mean",
        time_window: str = "1h",
    ) -> Dict[str, Any]:
        """Aggregate data from multiple sensors."""

        aggregated_data = {}

        for sensor_id in sensor_ids:
            readings = await self.get_sensor_data(sensor_id)

            if not readings:
                continue

            numeric_values = [
                reading.value
                for reading in readings
                if isinstance(reading.value, (int, float))
            ]

            if numeric_values:
                if aggregation_type == "mean":
                    aggregated_data[sensor_id] = sum(numeric_values) / len(
                        numeric_values
                    )
                elif aggregation_type == "max":
                    aggregated_data[sensor_id] = max(numeric_values)
                elif aggregation_type == "min":
                    aggregated_data[sensor_id] = min(numeric_values)
                elif aggregation_type == "sum":
                    aggregated_data[sensor_id] = sum(numeric_values)

        return {
            "aggregation_type": aggregation_type,
            "time_window": time_window,
            "data": aggregated_data,
            "timestamp": datetime.now().isoformat(),
        }

    def get_connected_sensors(self, tenant_id: str) -> List[SensorDevice]:
        """Get all connected sensors for a tenant."""
        return list(self.connected_sensors.values())


# Example sensor types that can be easily integrated
SUPPORTED_SENSOR_TYPES = {
    "temperature": {"unit": "celsius", "data_type": "float"},
    "humidity": {"unit": "percentage", "data_type": "float"},
    "pressure": {"unit": "hPa", "data_type": "float"},
    "accelerometer": {"unit": "m/s²", "data_type": "dict"},
    "gyroscope": {"unit": "rad/s", "data_type": "dict"},
    "camera": {"unit": "pixels", "data_type": "bytes"},
    "microphone": {"unit": "dB", "data_type": "bytes"},
    "gps": {"unit": "coordinates", "data_type": "dict"},
    "light": {"unit": "lux", "data_type": "float"},
    "proximity": {"unit": "cm", "data_type": "float"},
    "air_quality": {"unit": "ppm", "data_type": "dict"},
}
