import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import asyncio
from utils.logger import logger
from services.google_sheets import GoogleSheetsService
import json
import os

@dataclass
class MetricAlert:
    metric_name: str
    condition: str  # '>', '<', '>=', '<=', 'change>', 'change<'
    threshold: float
    message: str
    check_interval: int = 5  # минуты
    last_triggered: Optional[datetime] = None
    consecutive_triggers: int = 0
    required_triggers: int = 1  # сколько раз подряд должно сработать условие

    def check_condition(self, current_value: float, previous_value: float) -> bool:
        if 'change' in self.condition:
            if previous_value == 0:
                change_percent = 100 if current_value > 0 else 0
            else:
                change_percent = ((current_value - previous_value) / abs(previous_value)) * 100

            if self.condition == 'change>':
                return change_percent > self.threshold
            else:  # 'change<'
                return change_percent < self.threshold
        else:
            if self.condition == '>':
                return current_value > self.threshold
            elif self.condition == '<':
                return current_value < self.threshold
            elif self.condition == '>=':
                return current_value >= self.threshold
            elif self.condition == '<=':
                return current_value <= self.threshold
        return False

@dataclass
class MetricData:
    name: str
    current_value: float
    previous_value: float
    change_percent: float
    timestamp: datetime
    planned_value: Optional[float] = None

@dataclass
class ReportTemplate:
    name: str
    metrics: List[str]
    period: str  # 'day', 'week', 'month'
    include_charts: bool = True
    include_comparison: bool = True
    auto_send: bool = False
    send_time: Optional[str] = None  # "HH:MM" format
    send_days: Optional[List[int]] = None  # Days of week (0-6, where 0 is Monday)
    chat_id: Optional[int] = None  # Telegram chat ID for auto-sending

class MetricsTracker:
    def __init__(self, google_sheets_service: GoogleSheetsService):
        self.google_sheets = google_sheets_service
        self.metrics_history: Dict[str, List[MetricData]] = {}
        self.alerts: List[MetricAlert] = []
        self.update_task = None
        self.update_interval = 300  # 5 minutes
        self.report_templates: Dict[str, ReportTemplate] = self._load_templates()
        self.auto_report_task = None

    def _load_templates(self) -> Dict[str, ReportTemplate]:
        """Load saved report templates"""
        try:
            if os.path.exists('report_templates.json'):
                with open('report_templates.json', 'r') as f:
                    data = json.load(f)
                    templates = {}
                    for name, template_data in data.items():
                        # Convert days list if present
                        if 'send_days' in template_data and template_data['send_days']:
                            template_data['send_days'] = list(template_data['send_days'])
                        templates[name] = ReportTemplate(**template_data)
                    return templates
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
        return {}

    def save_template(self, template: ReportTemplate):
        """Save a new report template"""
        self.report_templates[template.name] = template
        try:
            with open('report_templates.json', 'w') as f:
                # Convert template to dict, handling Optional fields
                templates_dict = {}
                for name, tmpl in self.report_templates.items():
                    tmpl_dict = vars(tmpl)
                    # Convert days list to JSON-serializable format
                    if tmpl_dict.get('send_days'):
                        tmpl_dict['send_days'] = list(tmpl_dict['send_days'])
                    templates_dict[name] = tmpl_dict

                json.dump(templates_dict, f)
            logger.info(f"Saved template: {template.name}")
        except Exception as e:
            logger.error(f"Error saving template: {e}")

    def delete_template(self, template_name: str):
        """Delete a report template"""
        if template_name in self.report_templates:
            del self.report_templates[template_name]
            try:
                with open('report_templates.json', 'w') as f:
                    json.dump(
                        {name: vars(template) 
                         for name, template in self.report_templates.items()},
                        f
                    )
                logger.info(f"Deleted template: {template_name}")
            except Exception as e:
                logger.error(f"Error saving templates after deletion: {e}")

    async def compare_periods(self, metric_name: str, 
                            period1_start: datetime, period1_end: datetime,
                            period2_start: datetime, period2_end: datetime) -> Dict[str, Any]:
        """Compare metric values between two time periods"""
        try:
            if metric_name not in self.metrics_history:
                return {}

            period1_data = [
                m for m in self.metrics_history[metric_name]
                if period1_start <= m.timestamp <= period1_end
            ]
            period2_data = [
                m for m in self.metrics_history[metric_name]
                if period2_start <= m.timestamp <= period2_end
            ]

            if not period1_data or not period2_data:
                return {}

            period1_avg = np.mean([m.current_value for m in period1_data])
            period2_avg = np.mean([m.current_value for m in period2_data])
            change_percent = ((period2_avg - period1_avg) / period1_avg * 100 
                            if period1_avg != 0 else 0)

            return {
                'period1_avg': period1_avg,
                'period2_avg': period2_avg,
                'change_percent': change_percent,
                'trend': 'up' if change_percent > 0 else 'down' if change_percent < 0 else 'stable'
            }

        except Exception as e:
            logger.error(f"Error comparing periods for {metric_name}: {e}")
            return {}

    async def generate_comparison_report(self, period: str = 'day') -> Dict[str, Any]:
        """Generate a comparison report between current and previous period"""
        try:
            now = datetime.now()
            if period == 'day':
                period1_end = now
                period1_start = now - timedelta(days=1)
                period2_end = period1_start
                period2_start = period2_end - timedelta(days=1)
            elif period == 'week':
                period1_end = now
                period1_start = now - timedelta(days=7)
                period2_end = period1_start
                period2_start = period2_end - timedelta(days=7)
            elif period == 'month':
                period1_end = now
                period1_start = now - timedelta(days=30)
                period2_end = period1_start
                period2_start = period2_end - timedelta(days=30)
            else:
                raise ValueError(f"Invalid period: {period}")

            report = {}
            metrics = await self.google_sheets.get_metrics(include_plan=True)

            for metric_name in metrics.keys():
                comparison = await self.compare_periods(
                    metric_name, period1_start, period1_end, period2_start, period2_end
                )
                if comparison:
                    report[metric_name] = {
                        'comparison': comparison,
                        'current': metrics[metric_name].get('actual', 0),
                        'plan': metrics[metric_name].get('plan', 0)
                    }

            return report

        except Exception as e:
            logger.error(f"Error generating comparison report: {e}")
            return {}

    async def generate_report_from_template(self, template_name: str) -> Dict[str, Any]:
        """Generate a report using a saved template"""
        try:
            if template_name not in self.report_templates:
                raise ValueError(f"Template not found: {template_name}")

            template = self.report_templates[template_name]
            report = {
                'name': template.name,
                'timestamp': datetime.now().isoformat(),
                'metrics': {}
            }

            # Get current metrics
            current_metrics = await self.google_sheets.get_metrics(
                include_plan=template.include_comparison
            )

            for metric_name in template.metrics:
                if metric_name in current_metrics:
                    metric_data = {
                        'current': current_metrics[metric_name].get('actual', 0)
                    }

                    if template.include_comparison:
                        metric_data['plan'] = current_metrics[metric_name].get('plan', 0)
                        metric_data['plan_achievement'] = (
                            (metric_data['current'] / metric_data['plan'] * 100)
                            if metric_data['plan'] != 0 else 0
                        )

                    if template.include_charts:
                        history = self.get_metric_history(metric_name, 
                                                        hours=24 if template.period == 'day'
                                                        else 168 if template.period == 'week'
                                                        else 720)
                        metric_data['history'] = [
                            {'timestamp': m.timestamp.isoformat(),
                             'value': m.current_value}
                            for m in history
                        ]

                    report['metrics'][metric_name] = metric_data

            return report

        except Exception as e:
            logger.error(f"Error generating report from template: {e}")
            return {}

    async def _auto_send_reports(self):
        """Periodically check and send automated reports"""
        while True:
            try:
                current_time = datetime.now()
                for template_name, template in self.report_templates.items():
                    if not template.auto_send or not template.send_time or not template.chat_id:
                        continue

                    # Parse scheduled time
                    scheduled_hour, scheduled_minute = map(int, template.send_time.split(':'))

                    # Check if it's time to send
                    if (current_time.hour == scheduled_hour and 
                        current_time.minute == scheduled_minute and
                        (not template.send_days or current_time.weekday() in template.send_days)):

                        try:
                            report = await self.generate_report_from_template(template_name)
                            if report:
                                # Signal to bot to send report
                                logger.info(f"Auto-sending report '{template_name}' to chat {template.chat_id}")
                                # Note: actual sending is handled by the bot

                        except Exception as e:
                            logger.error(f"Error auto-sending report '{template_name}': {e}")

            except Exception as e:
                logger.error(f"Error in auto-report task: {e}")

            # Wait for next minute
            await asyncio.sleep(60)


    def start_periodic_updates(self):
        """Start periodic metric updates and auto-reports"""
        if self.update_task is None:
            self.update_task = asyncio.create_task(self._periodic_update())
            self.auto_report_task = asyncio.create_task(self._auto_send_reports())
            logger.info("Started periodic metrics updates and auto-reports")

    def stop_periodic_updates(self):
        """Stop periodic metric updates and auto-reports"""
        if self.update_task:
            self.update_task.cancel()
            self.update_task = None
        if self.auto_report_task:
            self.auto_report_task.cancel()
            self.auto_report_task = None
        logger.info("Stopped periodic metrics updates and auto-reports")

    async def _periodic_update(self):
        """Periodically fetch and update metrics"""
        while True:
            try:
                metrics = await self.google_sheets.get_metrics(include_plan=True)
                for name, value_data in metrics.items():
                    current_value = value_data.get('actual', 0)
                    planned_value = value_data.get('plan', None)
                    # Get previous value
                    prev_value = (self.metrics_history[name][-1].current_value 
                                if name in self.metrics_history and self.metrics_history[name] 
                                else current_value)

                    # Update metric
                    await self.update_metric(name, current_value, prev_value, planned_value)

                logger.info("Successfully updated metrics")

            except Exception as e:
                logger.error(f"Error in periodic update: {str(e)}")

            await asyncio.sleep(self.update_interval)

    def add_alert(self, metric_name: str, condition: str, threshold: float, message: str):
        """Add a new alert for a metric"""
        alert = MetricAlert(metric_name, condition, threshold, message)
        self.alerts.append(alert)
        logger.info(f"Added alert for {metric_name}: {condition} {threshold}")

    def check_alerts(self, metric_data: MetricData) -> List[str]:
        """Check if any alerts should be triggered for the given metric with improved logic"""
        triggered_alerts = []
        for alert in self.alerts:
            if alert.metric_name == metric_data.name:
                # Проверяем интервал между алертами
                if (alert.last_triggered and 
                    datetime.now() - alert.last_triggered < timedelta(minutes=alert.check_interval)):
                    continue

                # Проверяем условие
                condition_met = alert.check_condition(
                    metric_data.current_value,
                    metric_data.previous_value
                )

                if condition_met:
                    alert.consecutive_triggers += 1
                else:
                    alert.consecutive_triggers = 0

                # Проверяем, достаточно ли последовательных срабатываний
                if alert.consecutive_triggers >= alert.required_triggers:
                    alert.last_triggered = datetime.now()
                    alert.consecutive_triggers = 0

                    # Формируем сообщение с дополнительной информацией
                    message = alert.message.format(
                        value=metric_data.current_value,
                        threshold=alert.threshold,
                        change_percent=metric_data.change_percent
                    )

                    if metric_data.planned_value:
                        plan_achievement = (metric_data.current_value / metric_data.planned_value * 100 
                                         if metric_data.planned_value != 0 else 0)
                        message += f"\nВыполнение плана: {plan_achievement:.1f}%"

                    triggered_alerts.append(message)

        return triggered_alerts

    def calculate_trend(self, metric_name: str, window: int = 5) -> Optional[float]:
        """Calculate trend for a metric using linear regression with improved accuracy"""
        if metric_name not in self.metrics_history:
            return None

        history = self.metrics_history[metric_name]
        if len(history) < 2:
            return None

        # Get last n values
        values = [m.current_value for m in history[-window:]]
        if len(values) < 2:
            return None

        # Calculate trend using numpy with normalized time series
        x = np.arange(len(values))
        y = np.array(values)

        # Normalize values to prevent numerical instability
        y_mean = np.mean(y)
        y_std = np.std(y) if np.std(y) != 0 else 1
        y_normalized = (y - y_mean) / y_std

        # Calculate trend
        z = np.polyfit(x, y_normalized, 1)

        # Convert back to original scale
        trend = z[0] * y_std

        # Add confidence calculation
        r_squared = np.corrcoef(x, y_normalized)[0,1] ** 2

        # Return trend only if confidence is high enough
        if r_squared > 0.5:  # можно настроить порог уверенности
            return trend
        else:
            return 0.0  # тренд неясен

    async def update_metric(self, name: str, current_value: float, previous_value: float, planned_value: Optional[float]=None) -> Tuple[List[str], Optional[float]]:
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
                timestamp=datetime.now(),
                planned_value=planned_value
            )

            # Add to history
            if name not in self.metrics_history:
                self.metrics_history[name] = []
            self.metrics_history[name].append(metric_data)

            # Keep only last 24 hours of data
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history[name] = [
                m for m in self.metrics_history[name] 
                if m.timestamp > cutoff_time
            ]

            # Check alerts
            alerts = self.check_alerts(metric_data)

            # Calculate trend
            trend = self.calculate_trend(name)

            logger.info(f"Updated metric {name}: {current_value} (change: {change_percent:.2f}%)")
            return alerts, trend

        except Exception as e:
            logger.error(f"Error updating metric {name}: {str(e)}")
            return [], None

    async def generate_report(self) -> List[Dict[str, Any]]:
        """Generate a comprehensive report of all metrics"""
        report = []

        try:
            # Fetch latest metrics
            current_metrics = await self.google_sheets.get_metrics(include_plan=True)

            for metric_name, current_value_data in current_metrics.items():
                if metric_name not in self.metrics_history:
                    continue

                history = self.metrics_history[metric_name]
                if not history:
                    continue

                latest = history[-1]
                trend = self.calculate_trend(metric_name)

                metric_report = {
                    'name': metric_name,
                    'current_value': current_value_data.get('actual', 0),
                    'previous_value': latest.previous_value,
                    'change_percent': latest.change_percent,
                    'trend': trend if trend is not None else 0.0,
                    'trend_direction': 'up' if trend and trend > 0 else 'down' if trend and trend < 0 else 'stable',
                    'alerts': self.check_alerts(latest),
                    'planned_value': current_value_data.get('plan', None)

                }

                report.append(metric_report)

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")

        return report

    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[MetricData]:
        """Get historical data for a specific metric"""
        if metric_name not in self.metrics_history:
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history[metric_name] if m.timestamp > cutoff_time]

    async def analyze_metric_changes(self, metric_name: str, period: str = 'day') -> Dict[str, Any]:
        """Analyze changes in metric with detailed statistics"""
        try:
            if metric_name not in self.metrics_history:
                return {}

            # Определяем временной интервал
            now = datetime.now()
            if period == 'day':
                start_time = now - timedelta(days=1)
            elif period == 'week':
                start_time = now - timedelta(days=7)
            elif period == 'month':
                start_time = now - timedelta(days=30)
            else:
                raise ValueError(f"Invalid period: {period}")

            # Получаем историю за период
            history = [m for m in self.metrics_history[metric_name] 
                      if m.timestamp >= start_time]

            if not history:
                return {}

            values = [m.current_value for m in history]

            # Базовая статистика
            analysis = {
                'current_value': history[-1].current_value,
                'min_value': min(values),
                'max_value': max(values),
                'average': np.mean(values),
                'median': np.median(values),
                'std_dev': np.std(values),
                'total_change': history[-1].current_value - history[0].current_value,
                'change_percent': ((history[-1].current_value - history[0].current_value) / 
                                 history[0].current_value * 100 if history[0].current_value != 0 else 0)
            }

            # Анализ тренда
            trend = self.calculate_trend(metric_name)
            analysis['trend'] = {
                'direction': 'up' if trend > 0 else 'down' if trend < 0 else 'stable',
                'strength': abs(trend) if trend else 0
            }

            # Анализ волатильности
            changes = np.diff(values)
            analysis['volatility'] = {
                'daily_changes': list(changes),
                'average_daily_change': np.mean(np.abs(changes)) if len(changes) > 0 else 0,
                'max_daily_change': max(np.abs(changes)) if len(changes) > 0 else 0
            }

            # Прогноз на следующий период
            if len(values) >= 3:
                x = np.arange(len(values))
                z = np.polyfit(x, values, 2)
                p = np.poly1d(z)
                next_value = p(len(values))
                analysis['forecast'] = {
                    'next_value': max(0, next_value),  # не допускаем отрицательных значений
                    'confidence': min(1.0, 1.0 - np.std(values) / np.mean(values) if np.mean(values) != 0 else 0)
                }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing metric changes: {str(e)}")
            return {}