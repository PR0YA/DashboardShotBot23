import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from utils.logger import logger
from services.google_sheets import GoogleSheetsService

@dataclass
class MetricAlert:
    metric_name: str
    condition: str  # '>', '<', '>=', '<='
    threshold: float
    message: str

@dataclass
class MetricData:
    name: str
    current_value: float
    previous_value: float
    change_percent: float
    timestamp: datetime

class MetricsTracker:
    def __init__(self, google_sheets_service: GoogleSheetsService):
        self.google_sheets = google_sheets_service
        self.metrics_history: Dict[str, List[MetricData]] = {}
        self.alerts: List[MetricAlert] = []
        
    def add_alert(self, metric_name: str, condition: str, threshold: float, message: str):
        """Add a new alert for a metric"""
        alert = MetricAlert(metric_name, condition, threshold, message)
        self.alerts.append(alert)
        logger.info(f"Added alert for {metric_name}: {condition} {threshold}")
    
    def check_alerts(self, metric_data: MetricData) -> List[str]:
        """Check if any alerts should be triggered for the given metric"""
        triggered_alerts = []
        for alert in self.alerts:
            if alert.metric_name == metric_data.name:
                condition_met = False
                if alert.condition == '>':
                    condition_met = metric_data.current_value > alert.threshold
                elif alert.condition == '<':
                    condition_met = metric_data.current_value < alert.threshold
                elif alert.condition == '>=':
                    condition_met = metric_data.current_value >= alert.threshold
                elif alert.condition == '<=':
                    condition_met = metric_data.current_value <= alert.threshold
                
                if condition_met:
                    triggered_alerts.append(alert.message.format(
                        value=metric_data.current_value,
                        threshold=alert.threshold
                    ))
        
        return triggered_alerts
    
    def calculate_trend(self, metric_name: str, window: int = 5) -> Optional[float]:
        """Calculate trend for a metric using linear regression"""
        if metric_name not in self.metrics_history:
            return None
            
        history = self.metrics_history[metric_name]
        if len(history) < 2:
            return None
            
        # Get last n values
        values = [m.current_value for m in history[-window:]]
        if len(values) < 2:
            return None
            
        # Calculate trend using numpy
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        return z[0]  # Return slope
        
    def update_metric(self, name: str, current_value: float, previous_value: float) -> Tuple[List[str], float]:
        """Update metric value and return any triggered alerts and trend"""
        try:
            # Calculate change percentage
            if previous_value != 0:
                change_percent = ((current_value - previous_value) / abs(previous_value)) * 100
            else:
                change_percent = 0 if current_value == 0 else 100
                
            # Create metric data
            metric_data = MetricData(
                name=name,
                current_value=current_value,
                previous_value=previous_value,
                change_percent=change_percent,
                timestamp=datetime.now()
            )
            
            # Add to history
            if name not in self.metrics_history:
                self.metrics_history[name] = []
            self.metrics_history[name].append(metric_data)
            
            # Check alerts
            alerts = self.check_alerts(metric_data)
            
            # Calculate trend
            trend = self.calculate_trend(name)
            
            logger.info(f"Updated metric {name}: {current_value} (change: {change_percent:.2f}%)")
            return alerts, trend
            
        except Exception as e:
            logger.error(f"Error updating metric {name}: {str(e)}")
            return [], 0.0
    
    async def generate_report(self) -> List[Dict]:
        """Generate a comprehensive report of all metrics"""
        report = []
        
        for metric_name, history in self.metrics_history.items():
            if not history:
                continue
                
            latest = history[-1]
            trend = self.calculate_trend(metric_name)
            
            metric_report = {
                'name': metric_name,
                'current_value': latest.current_value,
                'previous_value': latest.previous_value,
                'change_percent': latest.change_percent,
                'trend': trend if trend is not None else 0.0,
                'trend_direction': 'up' if trend and trend > 0 else 'down' if trend and trend < 0 else 'stable',
                'alerts': self.check_alerts(latest)
            }
            
            report.append(metric_report)
            
        return report
