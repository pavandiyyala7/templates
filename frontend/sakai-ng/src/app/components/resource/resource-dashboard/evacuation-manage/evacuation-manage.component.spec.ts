import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvacuationManageComponent } from './evacuation-manage.component';

describe('EvacuationManageComponent', () => {
  let component: EvacuationManageComponent;
  let fixture: ComponentFixture<EvacuationManageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [EvacuationManageComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(EvacuationManageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
