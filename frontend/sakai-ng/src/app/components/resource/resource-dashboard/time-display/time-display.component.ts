import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';

@Component({
  selector: 'app-time-display',
  standalone: true,
  templateUrl: './time-display.component.html',
  styleUrl: './time-display.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush  // 🚀 Prevents unnecessary re-renders
})
export class TimeDisplayComponent implements OnInit, OnDestroy {
  currentDate: string = '';
  currentTime: string = '';
  private intervalId: any;

  constructor(private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.updateTime();
    this.intervalId = setInterval(() => this.updateTime(), 1000);
  }

  ngOnDestroy(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  updateTime() {
    const now = new Date();
    this.currentDate = now.toLocaleDateString('en-GB').split('/').join('-');
    this.currentTime = now.toLocaleTimeString('en-GB', { hour12: false });
    this.cdr.markForCheck();  // ✅ Only updates this component, NOT the entire page
  }
}
