from datetime import datetime, timedelta, time
from dataclasses import dataclass
from typing import Optional, Tuple
from functools import reduce
import operator
from django.db.models import Q, F, Max
from tqdm import tqdm
import gc
from django.db import models, transaction
from django.utils import timezone
from django.utils.timezone import make_aware, timezone, now

from config.models import AutoShift, Shift
from resource.models import Employee, Logs, Attendance, LastLogId
from value_config import WEEK_OFF_CONFIG

import logging

logger = logging.getLogger(__name__)

@dataclass
class ShiftWindow:
    name: str
    start_time: datetime
    end_time: datetime
    start_window: datetime
    end_window: datetime
    start_time_with_grace: datetime
    end_time_with_grace: datetime
    overtime_before_start: timedelta
    overtime_after_end: timedelta
    half_day_threshold: timedelta

class AttendanceProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.auto_shifts = list(AutoShift.objects.all())
        self.auto_shift_dict = {shift.name: shift for shift in self.auto_shifts}
        self.shifts = {shift.id: shift for shift in Shift.objects.all()}
        self.employees = {emp.employee_id: emp for emp in Employee.objects.all()}

    @transaction.atomic
    def process_new_logs(self) -> bool:
        try:
            last_log_id_record = LastLogId.objects.select_for_update().first()
            if not last_log_id_record:
                last_log_id_record = LastLogId.objects.create(last_log_id=0)

            last_processed_id = last_log_id_record.last_log_id
            new_logs = Logs.objects.filter(id__gt=last_processed_id).order_by('log_datetime')
            print(f"Processing new logs {new_logs}")

            if not new_logs:
                return True

            # Process logs in batches
            batch_size = 10000
            processed_logs = []

            # Calculate total number of logs
            total_logs = new_logs.count()

            # Use tqdm to show progress
            with tqdm(total=total_logs, desc="Processing logs", unit="log") as pbar:
                for i in range(0, total_logs, batch_size):
                    batch = new_logs[i:i + batch_size]
                    for log in batch:
                        if self.process_single_log(log):
                            processed_logs.append(log.id)
                        pbar.update(1)  # Update progress bar for each log

            if processed_logs:
                last_log_id_record.last_log_id = max(processed_logs)
                last_log_id_record.save()

            return True
        except Exception as e:
            self.logger.error(f"Error in process_new_logs: {str(e)}")
            return False

    def process_single_log(self, log: Logs, is_manual=False) -> bool:
        """Process a single attendance log."""
        print(f"Processing log for employee: {log} {log.employeeid}, Time: {log.log_datetime}, Direction: {log.direction}, Manual: {is_manual}")

        if not log.employeeid:
            # self.logger.error("Empty employee ID in log")
            return False

        try:
            # employee = Employee.objects.get(employee_id=log.employeeid)
            employee = self.employees.get(log.employeeid)
        except Employee.DoesNotExist:
            # self.logger.error(f"Employee with ID: {log.employeeid} not found.")
            return False
        except Exception as e:
            # self.logger.error(f"Error fetching employee {log.employeeid}: {str(e)}")
            return False

        try:
            if employee.shift:
                # Handle case when employee is assigned to a fixed shift  
                if is_manual:
                    if log.direction.lower() == 'in device':
                        return self._handle_in_log_fixedshift(employee, log, is_manual=True)
                    elif log.direction.lower() == 'out device':
                        return self._handle_out_log_fixedshift(employee, log, is_manual=True)
                else:
                    if log.direction.lower() == 'in device':  
                        return self._handle_in_log_fixedshift(employee, log, is_manual=False)  
                    elif log.direction.lower() == 'out device':  
                        return self._handle_out_log_fixedshift(employee, log, is_manual=False)  
            else:  
                # Handle auto-shift processing  
                if is_manual:
                    if log.direction.lower() == 'in device':
                        return self._handle_in_log_autoshift(employee, log, is_manual=True)
                    elif log.direction.lower() == 'out device':
                        return self._handle_out_log_autoshift(employee, log, is_manual=True)
                else:
                    if log.direction.lower() == 'in device':
                        return self._handle_in_log_autoshift(employee, log, is_manual=False)  
                    elif log.direction.lower() == 'out device':  
                        return self._handle_out_log_autoshift(employee, log, is_manual=False)  
            return False

        except Exception as e:
            # self.logger.error(f"Error processing log for employee {log.employeeid}: {str(e)}")
            return False

    def _handle_in_log_autoshift(self, employee: Employee, log: Logs, is_manual: bool = False) -> bool:
        """Handle incoming attendance log."""
        try:
            if timezone.is_aware(log.log_datetime):
                log_datetime = timezone.make_naive(log.log_datetime)
            else:
                log_datetime = log.log_datetime

            log_time = log_datetime.time()
            log_date = log_datetime.date()

            print(f"dfgfdgdfg employee {employee.employee_id} on {log_date} at {log_time}")

            # Find the matching shift for this IN punch
            for auto_shift in self.auto_shifts:
                try:
                    shift_window = self._calculate_autoshift_window(auto_shift, log_datetime)

                    if shift_window.start_window <= log_datetime <= shift_window.end_window:
                        with transaction.atomic():  # Use a nested atomic block
                            existing_attendance = Attendance.objects.select_for_update().filter(
                                employeeid=employee,
                                logdate=shift_window.start_time.date()
                            ).first()

                            if existing_attendance:
                                print(f"Existing attendance record found for employee {employee.employee_id}: first_logtime={existing_attendance.first_logtime}, last_logtime={existing_attendance.last_logtime}")
                                if existing_attendance.first_logtime is None and existing_attendance.last_logtime is None:
                                    attendance = existing_attendance
                                    attendance.first_logtime = log_time
                                    attendance.shift = auto_shift.name
                                    attendance.direction = 'Manual' if is_manual else 'Machine'
                                    attendance.shift_status = 'MP'
                                elif existing_attendance.last_logtime is not None and existing_attendance.first_logtime is None:
                                    # Handle case where last_logtime is already set but first_logtime is null
                                    return self._handle_late_in_log_autoshift(employee, log, existing_attendance, auto_shift, is_manual)
                                else:
                                    return True # Already has first logtime, nothing to update for IN log
                            else:
                                print(f"No existing attendance record found for employee {employee.employee_id} on {log_date}. Creating new record.")
                                attendance = Attendance(
                                    employeeid=employee,
                                    logdate=log_date,
                                    first_logtime=log_time,
                                    shift=auto_shift.name,
                                    direction='Manual' if is_manual else 'Machine',
                                    shift_status='MP'
                                )

                            if log_datetime > shift_window.start_time_with_grace:
                                attendance.late_entry = log_datetime - shift_window.start_time

                            attendance.save()
                            return True

                except Exception as e:
                    # self.logger.error(f"Error processing shift {auto_shift.name} for employee {employee.employee_id} in _handle_in_log_autoshift: {str(e)}")
                    continue

            return True

        except Exception as e:
            # self.logger.exception(f"Error in _handle_in_log_autoshift for employee {employee.employee_id}: {str(e)}")
            return False

    def _handle_late_in_log_autoshift(self, employee: Employee, log: Logs, existing_attendance: Attendance, auto_shift: AutoShift, is_manual: bool = False) -> bool:
        """
        Handles the case where an 'IN' log arrives for an attendance record that already has a 'last_logtime' but no 'first_logtime'.
        This typically happens when the 'OUT' log was processed before the 'IN' log.
        """
        print(f"Handling late IN log for employee {employee.employee_id} with existing attendance record: {existing_attendance}")
        try:
            if timezone.is_aware(log.log_datetime):
                log_datetime = timezone.make_naive(log.log_datetime)
            else:
                log_datetime = log.log_datetime

            log_time = log_datetime.time()

            existing_attendance.first_logtime = log_time
            existing_attendance.direction = 'Manual' if is_manual else 'Machine'
            existing_attendance.shift = auto_shift.name # Ensure shift is set if not already

            # Recalculate attendance details now that we have both IN and OUT times
            in_datetime = datetime.combine(existing_attendance.logdate, existing_attendance.first_logtime)
            out_datetime = datetime.combine(existing_attendance.logdate, existing_attendance.last_logtime)

            # Basic validation - ensure IN is not after OUT (can adjust if needed for specific night shift scenarios)
            if in_datetime > out_datetime:
                # Handle cases where IN time is incorrectly after OUT time, maybe log a warning or adjust dates if logic dictates
                self.logger.warning(f"IN log time {in_datetime} is after OUT log time {out_datetime} for employee {employee.employee_id} on {existing_attendance.logdate}. Manual intervention may be needed.")
                return False # Or handle as per business logic - maybe swap times or just log

            total_time = out_datetime - in_datetime

            if auto_shift.include_lunch_break_in_half_day:
                total_time -= auto_shift.lunch_duration
                if total_time < timedelta():
                    total_time = timedelta()
                else:
                    existing_attendance.total_time = total_time
            else:
                if auto_shift.include_lunch_break_in_full_day:
                    total_time -= auto_shift.lunch_duration
                    if total_time < timedelta():
                        total_time = timedelta()
                    else:
                        existing_attendance.total_time = total_time
                else:
                    existing_attendance.total_time = total_time

            shift_start = datetime.combine(in_datetime.date(), auto_shift.start_time)
            if not auto_shift.is_night_shift():
                if auto_shift.start_time == time(0, 0):
                    if in_datetime.time() > auto_shift.end_time:
                        shift_end = datetime.combine(in_datetime.date() + timedelta(days=1), auto_shift.end_time)
                else:
                    shift_end = datetime.combine(in_datetime.date(), auto_shift.end_time)
            else:
                shift_end = datetime.combine(in_datetime.date() + timedelta(days=1), auto_shift.end_time)

            # Calculate early exit
            if out_datetime < shift_end:
                existing_attendance.early_exit = shift_end - out_datetime
            else:
                existing_attendance.early_exit = None

            # Overtime calculation
            overtime_threshold_before = shift_start - auto_shift.overtime_threshold_before_start
            overtime_threshold_after = shift_end + auto_shift.overtime_threshold_after_end

            overtime_before = max(timedelta(), shift_start - in_datetime) if in_datetime < overtime_threshold_before else timedelta()
            overtime_after = max(timedelta(), out_datetime - shift_end) if out_datetime > overtime_threshold_after else timedelta()

            # Shift status determination - reuse logic from _handle_out_log_autoshift for status update
            first_weekoff = employee.first_weekly_off
            if isinstance(first_weekoff, str):
                try:
                    first_weekoff = int(first_weekoff)
                except ValueError:
                    raise ValueError
            is_weekoff = first_weekoff
            absent_threshold = auto_shift.absent_threshold
            half_day_threshold = auto_shift.half_day_threshold
            full_day_threshold = auto_shift.full_day_threshold
            weekoff_days = [is_weekoff] if is_weekoff is not None else WEEK_OFF_CONFIG.get('DEFAULT_WEEK_OFF', [])

            if existing_attendance.logdate.weekday() in weekoff_days:
                existing_attendance.overtime = total_time
            else:                        
                existing_attendance.overtime = overtime_before + overtime_after if (overtime_before + overtime_after) > timedelta() else None
            if existing_attendance.logdate.weekday() in weekoff_days:
                existing_attendance.overtime = total_time
            else:                                            
                existing_attendance.overtime = overtime_before + overtime_after if (overtime_before + overtime_after) > timedelta() else None

            if existing_attendance.logdate.weekday() in weekoff_days:
                existing_attendance.shift_status = 'WW'
            elif absent_threshold is not None and total_time < absent_threshold:
                existing_attendance.shift_status = 'A'
            elif half_day_threshold is not None and total_time < half_day_threshold:
                existing_attendance.shift_status = 'HD'
            elif full_day_threshold is not None and total_time < full_day_threshold:
                existing_attendance.shift_status = 'IH'
            else:
                existing_attendance.shift_status = 'P' if total_time >= full_day_threshold else ''

            existing_attendance.save()
            return True

        except Exception as e:
            self.logger.error(f"Error in _handle_late_in_log_autoshift for employee {employee.employee_id}: {str(e)}")
            return False

    def _handle_out_log_autoshift(self, employee: Employee, log: Logs, is_manual: bool = False) -> bool:
        """
        Handle outgoing attendance log.
        Updates the last OUT time of an existing attendance record or creates a new OUT log if no valid IN found.
        """
        try:
            # Convert to naive datetime if timezone-aware
            if timezone.is_aware(log.log_datetime):
                log_datetime = timezone.make_naive(log.log_datetime)
            else:
                log_datetime = log.log_datetime


            log_time = log_datetime.time()
            log_date = log_datetime.date()

            # First check if there are any earlier logs for this day
            attendance = Attendance.objects.filter(
                employeeid=employee,
                logdate=log_date,
                first_logtime__isnull=False
            ).first()

            if not attendance:
                prev_date = log_date - timedelta(days=1)
                attendance = Attendance.objects.filter(
                    employeeid=employee,
                    logdate=prev_date,
                    first_logtime__isnull=False,
                    # last_logtime__isnull=True  # Must not have an OUT punch already
                ).first()

                if not attendance:
                    # Create or update an OUT log with shift_status as 'MP' if no valid IN found
                    attendance = Attendance.objects.update_or_create(
                        employeeid=employee,
                        logdate=log_date,
                        defaults={
                            'last_logtime': log_time,
                            'shift': '',  # Or set it as needed
                            'direction': 'Manual' if is_manual else 'Machine',
                            'shift_status': 'MP'
                        }
                    )[0]
                    attendance.save()

            if not attendance:
                # self.logger.warning(f"No valid IN log found for employee {employee.employee_id} before OUT")
                return True

            # Get the shift details
            try:
                # auto_shift = AutoShift.objects.get(name=attendance.shift)
                auto_shift = self.auto_shift_dict.get(attendance.shift)
            except AutoShift.DoesNotExist:
                # self.logger.error(f"Shift {attendance.shift} not found for employee {employee.employee_id}")
                return False

            # Check if this is a valid OUT punch for the attendance
            in_datetime = datetime.combine(attendance.logdate, attendance.first_logtime)
            out_datetime = log_datetime
            # Calculate shift end time based on shift type
            if auto_shift.is_night_shift():
                if auto_shift.start_time > auto_shift.end_time:
                    # Night shift crossing midnight
                    shift_end = datetime.combine(
                        attendance.logdate + timedelta(days=1),
                        auto_shift.end_time
                    )
                else:
                    # Night shift within same calendar date
                    shift_end = datetime.combine(
                        attendance.logdate,
                        auto_shift.end_time
                    )
            else:
                # Regular day shift
                shift_end = datetime.combine(
                    attendance.logdate,
                    auto_shift.end_time
                )
            
            first_weekoff = employee.first_weekly_off
            if isinstance(first_weekoff, str):
                try:
                    first_weekoff = int(first_weekoff)
                except ValueError:
                    raise ValueError
            is_weekoff = first_weekoff
            absent_threshold = auto_shift.absent_threshold
            half_day_threshold = auto_shift.half_day_threshold
            full_day_threshold = auto_shift.full_day_threshold

            # Update attendance if this OUT is after IN and the latest one
            if out_datetime > in_datetime:
                if not attendance.last_logtime or out_datetime.time() > attendance.last_logtime:
                    attendance.last_logtime = log_time
                    attendance.direction = 'Manual' if is_manual else 'Machine'

                    # Calculate total time
                    total_time = out_datetime - in_datetime

                    if auto_shift.include_lunch_break_in_half_day:
                        total_time -= auto_shift.lunch_duration
                        if total_time < timedelta():
                            total_time = timedelta()
                        else:
                            attendance.total_time = total_time
                    else:
                        if auto_shift.include_lunch_break_in_full_day:
                            total_time -= auto_shift.lunch_duration
                            if total_time < timedelta():
                                total_time = timedelta()
                            else:
                                attendance.total_time = total_time
                        else:
                            attendance.total_time = total_time 

                    shift_start = datetime.combine(in_datetime.date(), auto_shift.start_time)
                    if not auto_shift.is_night_shift():
                        if auto_shift.start_time == time(0, 0):
                            if in_datetime.time() > auto_shift.end_time:
                                shift_end = datetime.combine(in_datetime.date() + timedelta(days=1), auto_shift.end_time)
                        else:
                            shift_end = datetime.combine(in_datetime.date(), auto_shift.end_time)
                    else:
                        shift_end = datetime.combine(in_datetime.date() + timedelta(days=1), auto_shift.end_time)
                    # shift_end = datetime.combine(in_datetime.date(), auto_shift.end_time) if auto_shift.night_shift

                    # Calculate early exit
                    if out_datetime < shift_end:
                        attendance.early_exit = shift_end - out_datetime
                    else:
                        attendance.early_exit = None

                    # Overtime calculation
                    overtime_threshold_before = shift_start - auto_shift.overtime_threshold_before_start
                    overtime_threshold_after = shift_end + auto_shift.overtime_threshold_after_end

                    overtime_before = max(timedelta(), shift_start - in_datetime) if in_datetime < overtime_threshold_before else timedelta()
                    overtime_after = max(timedelta(), out_datetime - shift_end) if out_datetime > overtime_threshold_after else timedelta()

                    
                    # Update status based on thresholds
                    weekoff_days = [is_weekoff] if is_weekoff is not None else WEEK_OFF_CONFIG.get('DEFAULT_WEEK_OFF', [])

                    if attendance.logdate.weekday() in weekoff_days:
                        attendance.overtime = total_time
                    else:                        
                        attendance.overtime = overtime_before + overtime_after if (overtime_before + overtime_after) > timedelta() else None

                    if attendance.logdate.weekday() in weekoff_days:
                        attendance.overtime = total_time
                    else:                                            
                        attendance.overtime = overtime_before + overtime_after if (overtime_before + overtime_after) > timedelta() else None

                    if attendance.logdate.weekday() in weekoff_days:
                        attendance.shift_status = 'WW'
                    elif absent_threshold is not None and total_time < absent_threshold:
                        attendance.shift_status = 'A'
                    elif half_day_threshold is not None and total_time < half_day_threshold:
                        attendance.shift_status = 'HD'
                    elif full_day_threshold is not None and total_time < full_day_threshold:
                        attendance.shift_status = 'IH'
                    else:
                        attendance.shift_status = 'P' if total_time >= full_day_threshold else ''

                            
                    # if attendance.logdate.weekday() in WEEK_OFF_CONFIG['DEFAULT_WEEK_OFF']:
                    #     attendance.shift_status = 'WW'
                    # else:
                    #     attendance.shift_status = 'P' if total_time > auto_shift.half_day_threshold else 'HD'

                    attendance.save()
                    # self.logger.info(
                    #     f"Updated attendance for employee {employee.employee_id}: "
                    #     f"Date: {attendance.logdate}, "
                    #     f"IN: {attendance.first_logtime}, "
                    #     f"OUT: {log_time}"
                    # )

            elif out_datetime < in_datetime:
                if not attendance.last_logtime or out_datetime.time() > attendance.last_logtime:
                    attendance.last_logtime = log_time
                    attendance.direction = 'Manual' if is_manual else 'Machine'

                    in_datetime = datetime.combine(attendance.logdate, attendance.first_logtime) - timedelta(days=1)
                    total_time = out_datetime - in_datetime

                    if auto_shift.include_lunch_break_in_half_day:
                        total_time -= auto_shift.lunch_duration
                        if total_time < timedelta():
                            total_time = timedelta()
                        else:
                            attendance.total_time = total_time
                    else:
                        if auto_shift.include_lunch_break_in_full_day:
                            total_time -= auto_shift.lunch_duration
                            if total_time < timedelta():
                                total_time = timedelta()
                            else:
                                attendance.total_time = total_time
                        else:
                            attendance.total_time = total_time      

                    if auto_shift.start_time == time(0, 0):
                        if in_datetime.time() > auto_shift.end_time:
                            in_datetime = datetime.combine(in_datetime.date() + timedelta(), auto_shift.start_time)              

                    shift_start = datetime.combine(in_datetime.date(), auto_shift.start_time)
                    if not auto_shift.is_night_shift():
                        if auto_shift.start_time == time(0, 0):
                            if in_datetime.time() > auto_shift.end_time:
                                shift_end = datetime.combine(in_datetime.date() + timedelta(days=1), auto_shift.end_time)
                        else:
                            shift_end = datetime.combine(in_datetime.date(), auto_shift.end_time)
                    else:
                        shift_end = datetime.combine(in_datetime.date() + timedelta(days=1), auto_shift.end_time)

                    # Calculate early exit
                    if out_datetime < shift_end:
                        attendance.early_exit = shift_end - out_datetime
                    else:
                        attendance.early_exit = None

                    # Overtime calculation
                    overtime_threshold_before = shift_start - auto_shift.overtime_threshold_before_start
                    overtime_threshold_after = shift_end + auto_shift.overtime_threshold_after_end

                    overtime_before = max(timedelta(), shift_start - in_datetime) if in_datetime < overtime_threshold_before else timedelta()
                    overtime_after = max(timedelta(), out_datetime - shift_end) if out_datetime > overtime_threshold_after else timedelta()
                    
                    # Update status based on thresholds
                    weekoff_days = [is_weekoff] if is_weekoff is not None else WEEK_OFF_CONFIG.get('DEFAULT_WEEK_OFF', [])

                    if attendance.logdate.weekday() in weekoff_days:
                        attendance.overtime = total_time
                    else:                        
                        attendance.overtime = overtime_before + overtime_after if (overtime_before + overtime_after) > timedelta() else None

                    if attendance.logdate.weekday() in weekoff_days:
                        attendance.shift_status = 'WW'
                    elif absent_threshold is not None and total_time < absent_threshold:
                        attendance.shift_status = 'A'
                    elif half_day_threshold is not None and total_time < half_day_threshold:
                        attendance.shift_status = 'HD'
                    elif full_day_threshold is not None and total_time < full_day_threshold:
                        attendance.shift_status = 'IH'
                    else:
                        attendance.shift_status = 'P' if total_time >= full_day_threshold else ''

                            
                    # if attendance.logdate.weekday() in WEEK_OFF_CONFIG['DEFAULT_WEEK_OFF']:
                    #     attendance.shift_status = 'WW'
                    # else:
                    #     attendance.shift_status = 'P' if total_time > auto_shift.half_day_threshold else 'HD'

                    attendance.save()

            return True

        except Exception as e:
            # self.logger.error(f"Error in _handle_out_log_autoshift for employee {employee.employee_id}: {str(e)}")
            return False


    def _calculate_autoshift_window(self, auto_shift: AutoShift, log_datetime: datetime) -> ShiftWindow:
        """Calculate shift time windows considering both date and time."""
        try:
            # Ensure we're working with naive datetime
            if timezone.is_aware(log_datetime):
                log_datetime = timezone.make_naive(log_datetime)

            base_date = log_datetime.date()
            log_time = log_datetime.time()

            name = auto_shift.name

            # Special handling for midnight shift (00:00 start time)
            if auto_shift.start_time == time(0, 0):
                # If log time is between 23:00 and midnight
                if time(23, 0) <= log_time <= time(23, 59, 59):
                    base_date = base_date + timedelta(days=1)
            
            if auto_shift.end_time == time(0, 0):
                # If log time is between midnight and 01:00
                if time(0, 0) <= log_time <= time(1, 0):
                    base_date = base_date - timedelta(days=1)

            # # Regular night shift handling
            # elif auto_shift.is_night_shift():
            #     if auto_shift.start_time > auto_shift.end_time:
            #         # For logs between shift start (e.g., 22:00) and midnight
            #         if log_time >= auto_shift.start_time:
            #             base_date = base_date + timedelta(days=1)
            #         # For logs between midnight and shift end (e.g., 07:00)
            #         elif log_time <= auto_shift.end_time:
            #             base_date = base_date
            #     else:  # Night shift within same calendar date
            #         if not (auto_shift.start_time <= log_time <= auto_shift.end_time):
            #             base_date = base_date + timedelta(days=1)

            # Calculate start and end times
            start_time = datetime.combine(base_date, auto_shift.start_time)
            end_time = datetime.combine(
                base_date + timedelta(days=1) if auto_shift.is_night_shift() and auto_shift.end_time < auto_shift.start_time else base_date,
                auto_shift.end_time
            )

            # Calculate window times
            if auto_shift.start_time == time(0, 0):
                start_window = start_time - timedelta(hours=1)  # One hour before midnight
            else:
                start_window = start_time - auto_shift.tolerance_start_time
            
            end_window = start_time + auto_shift.tolerance_end_time

            return ShiftWindow(
                name=name,
                start_time=start_time,
                end_time=end_time,
                start_window=start_window,
                end_window=end_window,
                start_time_with_grace=start_time + auto_shift.grace_period_at_start_time,
                end_time_with_grace=end_time - auto_shift.grace_period_at_end_time,
                overtime_before_start=auto_shift.overtime_threshold_before_start,
                overtime_after_end=auto_shift.overtime_threshold_after_end,
                half_day_threshold=auto_shift.half_day_threshold
            )
        except Exception as e:
            print(f"Error in _calculate_autoshift_window: {str(e)}")
            raise

    def _handle_in_log_fixedshift(self, employee: Employee, log: Logs, is_manual: bool = False) -> bool:
        """Handle incoming attendance log for fixed shift employees."""
        try:
            if timezone.is_aware(log.log_datetime):
                log_datetime = timezone.make_naive(log.log_datetime)
            else:
                log_datetime = log.log_datetime

            log_time = log_datetime.time()
            log_date = log_datetime.date()

            # Get the employee's fixed shift
            shift = self.shifts.get(employee.shift.id)
            if not shift:
                # self.logger.error(f"Shift not found for employee {employee.employee_id}")
                return False

            # Determine the correct date based on night shift logic
            # if shift.is_night_shift():
            #     # If current time is before end time, it belongs to previous day's shift
            #     if log_time <= shift.end_time:
            #         shift_date = log_date - timedelta(days=1)
            #     # If current time is after or equal to start time, it belongs to current day's shift
            #     elif log_time >= shift.start_time:
            #         shift_date = log_date
            #     else:
            #         # Time falls outside shift window
            #         return True
            # else:
            #     # For regular day shifts
            #     shift_date = log_date
            
            shift_date = log_date


            try:
                with transaction.atomic():
                    existing_attendance = Attendance.objects.select_for_update().filter(
                        employeeid=employee,
                        logdate=shift_date
                    ).first()

                    if existing_attendance:
                        if existing_attendance.first_logtime is None:
                            attendance = existing_attendance
                            attendance.first_logtime = log_time
                            attendance.shift = shift.name
                            attendance.direction = 'Manual' if is_manual else 'Machine'
                            attendance.shift_status = 'MP'
                        else:
                            return True
                    else:
                        attendance = Attendance(
                            employeeid=employee,
                            logdate=shift_date,
                            first_logtime=log_time,
                            shift=shift.name,
                            direction='Manual' if is_manual else 'Machine',
                            shift_status='MP'
                        )

                    # Calculate shift start time for the current date
                    shift_start = datetime.combine(shift_date, shift.start_time)
                    shift_start_with_grace = shift_start + shift.grace_period_at_start_time

                    # Check for late entry
                    if log_datetime > shift_start_with_grace:
                        attendance.late_entry = log_datetime - shift_start

                    attendance.save()
                    return True

            except Exception as e:
                # self.logger.error(f"Database error while processing IN log for employee {employee.employee_id}: {str(e)}")
                raise

        except Exception as e:
            # self.logger.error(f"Error in _handle_in_log_fixedshift for employee {employee.employee_id}: {str(e)}")
            return False
        
    def _handle_out_log_fixedshift(self, employee: Employee, log: Logs, is_manual: bool = False) -> bool:
        """
        Handle outgoing attendance log for fixed shift employees.
        Updates the last OUT time of an existing attendance record or creates a new OUT log if no valid IN found.
        """
        try:
            # Convert to naive datetime if timezone-aware
            if timezone.is_aware(log.log_datetime):
                log_datetime = timezone.make_naive(log.log_datetime)
            else:
                log_datetime = log.log_datetime

            log_time = log_datetime.time()
            log_date = log_datetime.date()

            # Get the employee's fixed shift
            shift = self.shifts.get(employee.shift.id)
            if not shift:
                self.logger.error(f"Shift not found for employee {employee.employee_id}")
                return False

            # Determine the correct logdate and check for existing attendance
            if shift.is_night_shift():
                # For night shifts, the log might belong to the previous day's shift
                if log_time < shift.start_time:
                    # If log time is before shift start, it belongs to previous day
                    log_date = log_date - timedelta(days=1)

            # Check for existing attendance records
            existing_attendance = Attendance.objects.filter(
                employeeid=employee,
                logdate=log_date
            ).first()

            # Handle different scenarios
            if existing_attendance:
                # If an attendance record exists and has an IN time
                if existing_attendance.first_logtime:
                    # Update the OUT time if it's later or not set
                    if not existing_attendance.last_logtime or log_time > existing_attendance.last_logtime:
                        existing_attendance.last_logtime = log_time
                        existing_attendance.direction = 'Manual' if is_manual else 'Machine'

                        # Calculate total time
                        in_datetime = datetime.combine(existing_attendance.logdate, existing_attendance.first_logtime)
                        out_datetime = datetime.combine(log_date, log_time)

                        # Adjust for night shifts crossing midnight
                        if shift.is_night_shift() and in_datetime > out_datetime:
                            in_datetime -= timedelta(days=1)

                        total_time = out_datetime - in_datetime

                        # Deduct lunch break if applicable
                        if shift.include_lunch_break_in_half_day or shift.include_lunch_break_in_full_day:
                            if shift.lunch_duration:
                                total_time -= shift.lunch_duration

                        existing_attendance.total_time = total_time

                        # Calculate shift timing
                        shift_start = datetime.combine(in_datetime.date(), shift.start_time)
                        shift_end = datetime.combine(out_datetime.date(), shift.end_time)
                        shift_end_with_grace = shift_end - shift.grace_period_at_end_time

                        # Early exit calculation
                        if out_datetime < shift_end_with_grace:
                            existing_attendance.early_exit = shift_end - out_datetime
                        else:
                            existing_attendance.early_exit = None

                        # Overtime calculation
                        overtime_threshold_before = shift_start - shift.overtime_threshold_before_start
                        overtime_threshold_after = shift_end + shift.overtime_threshold_after_end

                        overtime_before = max(timedelta(), shift_start - in_datetime) if in_datetime < overtime_threshold_before else timedelta()
                        overtime_after = max(timedelta(), out_datetime - shift_end) if out_datetime > overtime_threshold_after else timedelta()

                        # Shift status determination
                        first_weekoff = employee.first_weekly_off
                        weekoff_days = [first_weekoff] if first_weekoff is not None else WEEK_OFF_CONFIG.get('DEFAULT_WEEK_OFF', [])

                        if existing_attendance.logdate.weekday() in weekoff_days:
                            existing_attendance.overtime = total_time
                        else:                        
                            existing_attendance.overtime = overtime_before + overtime_after if (overtime_before + overtime_after) > timedelta() else None

                        if existing_attendance.logdate.weekday() in weekoff_days:
                            existing_attendance.shift_status = 'WW'
                        elif shift.absent_threshold is not None and total_time < shift.absent_threshold:
                            existing_attendance.shift_status = 'A'
                        elif shift.half_day_threshold is not None and total_time < shift.half_day_threshold:
                            existing_attendance.shift_status = 'HD'
                        elif shift.full_day_threshold is not None and total_time < shift.full_day_threshold:
                            existing_attendance.shift_status = 'IH'
                        else:
                            existing_attendance.shift_status = 'P'

                        existing_attendance.save()
                else:
                    # If no IN time, just update the OUT time
                    existing_attendance.last_logtime = log_time
                    existing_attendance.shift = shift.name
                    existing_attendance.direction = 'Manual' if is_manual else 'Machine'
                    existing_attendance.shift_status = 'MP'
                    existing_attendance.save()
            else:
                # Create a new attendance record with OUT time
                Attendance.objects.create(
                    employeeid=employee,
                    logdate=log_date,
                    last_logtime=log_time,
                    direction='Manual' if is_manual else 'Machine',
                    shift=shift.name,
                    shift_status='MP'
                )

            return True

        except Exception as e:
            self.logger.error(f"Error in _handle_out_log_fixedshift for employee {employee.employee_id}: {str(e)}", exc_info=True)
            return False