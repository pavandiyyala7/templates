import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmployeeStrengthComponent } from './employee-strength.component';

describe('EmployeeStrengthComponent', () => {
  let component: EmployeeStrengthComponent;
  let fixture: ComponentFixture<EmployeeStrengthComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [EmployeeStrengthComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(EmployeeStrengthComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
