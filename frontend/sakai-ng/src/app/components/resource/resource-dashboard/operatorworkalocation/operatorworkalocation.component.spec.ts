import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OperatorworkalocationComponent } from './operatorworkalocation.component';

describe('OperatorworkalocationComponent', () => {
  let component: OperatorworkalocationComponent;
  let fixture: ComponentFixture<OperatorworkalocationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [OperatorworkalocationComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(OperatorworkalocationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
