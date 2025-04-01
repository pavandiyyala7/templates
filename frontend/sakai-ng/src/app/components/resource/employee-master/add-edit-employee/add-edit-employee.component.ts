import { Component, OnInit, OnDestroy } from '@angular/core';
import { CountryService } from 'src/app/demo/service/country.service';
import { MessageService, ConfirmationService, ConfirmEventType } from 'primeng/api';
import { SharedService } from 'src/app/shared.service';
import { DataService } from 'src/app/service/dataservice/data.service';
import { ActivatedRoute } from '@angular/router';
import { DatePipe } from '@angular/common';
import { interval, Observable, Subscription, combineLatest, Subject } from 'rxjs';
import { distinctUntilChanged, startWith, switchMap, combineLatestWith, map, debounceTime } from 'rxjs/operators';

interface UploadEvent {
    originalEvent: Event;
    files: File[];
}

interface AccountTypes {
    name: string;
    code: string;
}

@Component({
  selector: 'app-add-edit-employee',
  standalone: false,
//   imports: [],
  templateUrl: './add-edit-employee.component.html',
  styleUrl: './add-edit-employee.component.scss'
})
export class AddEditEmployeeComponent implements OnInit, OnDestroy {

    uploadedFiles: any[] = [];
    currentFile?: File;
    message = '';
    preview = '';

    activeStepperNumber: number | undefined = 0;

    image_file_post: File | null = null;
    employee_id_error: boolean = false;

    account_types: any[] = [];
    categories: any[] = [];
    countries: any[] | undefined;
    shifts: any[] = [];
    companies: any[] = [];
    locations: any[] = [];
    departments: any[] = [];
    designations: any[] = [];
    divisions: any[] = [];
    subDivisions: any[] = [];
    shopfloors: any[] = [];
    marital_statuses: any[] = [];
    jobTypes: any[] = [];
    week_days: any[] = [];

    selectedCountry: string | undefined;
    agencyDisabled = true;
    agency: any;

    // private inputSubject = new Subject<string>();

    id: number | null = null;
    isEditMode: boolean = false;

    constructor(
        private service:SharedService,
        private countryService: CountryService,
        private messageService: MessageService,
        private datePipe: DatePipe,
        private dataService: DataService,
        private route: ActivatedRoute
    )
    { }

    ngOnInit(): void {

        this.getShiftslist();
        this.getCompaniesList();
        this.getLocationsList();
        this.getDepartmentsList();
        this.getDesignationsList();
        this.getDivisionsList();
        this.getSubDivisionsList();
        this.getShopfloorsList();

        this.getAllOptions();



 //   this.imageInfos = this.uploadService.getFiles();

        this.countryService.getCountries().then(countries => {
            this.countries = countries;
        });

        this.route.params.subscribe(params => {
            this.id = params['id'] ? +params['id'] : null; // Convert string to number if present
            this.isEditMode = this.id !== null && this.id !== 0; // id === 0 means "add" mode
        });

        // If in edit mode, fetch employee data based on the id
        if (this.isEditMode) {
          this.fetchEmployeeData(this.id);
        }

    }



    // fetch employee data with the id
    fetchEmployeeData(id: number) {
        // implement logic to fetch from service.fetchEmployee
        this.service.fetchEmployee(id).subscribe({
            next: (employee) => {
            console.log("asdds",employee)
            // set employee data to form fields
            this.preview = employee.profile_pic;
            this.employee_id = employee.employee_id;
            this.enroll_id = employee.device_enroll_id;
            this.employee_name = employee.employee_name;
            this.email = employee.email;
            this.mobile_no = employee.phone_no;
            this.pf_no = employee.pf_no;
            this.esi_no = employee.esi_no;
            this.insurance_no = employee.insurance_no;

            this.bank_name = employee.bank_name;
            this.branch_name = employee.bank_branch;
            this.account_no = employee.bank_account_no;
            this.account_name = employee.bank_account_name;
            this.account_type = employee.bank_account_type;
            this.ifsc_code = employee.ifsc_code;

            this.selectedCompany = employee.company ? this.companies.find(company => company.id === employee.company) : null;
            this.selectedLocation = employee.location ? this.locations.find(location => location.id === employee.location) : null;
            this.selectedCategory = employee.category ? this.categories.find(category => category.value === employee.category) : null;
            this.selectedDepartment = employee.department ? this.departments.find(department => department.id === employee.department) : null;
            this.selectedDesignation = employee.designation ? this.designations.find(designation => designation.id === employee.designation) : null;
            this.selectedDivision = employee.division ? this.divisions.find(division => division.id === employee.division) : null;
            this.selectedSubDivision = employee.subdivision ? this.subDivisions.find(subdivision => subdivision.id === employee.subdivision) : null;
            this.selectedShopfloor = employee.shopfloor ? this.shopfloors.find(shopfloor => shopfloor.id === employee.shopfloor) : null;
            this.selectedJobType = employee.job_type ? this.jobTypes.find(jobType => jobType.value === employee.job_type) : null;
            this.date_of_joining = employee.date_of_joining ? new Date(employee.date_of_joining) : null;
            this.date_of_leaving = employee.date_of_leaving ? new Date(employee.date_of_leaving) : null;
            this.jobStatus = employee.job_status;
            this.reason_for_leaving = employee.reason_for_leaving;

            this.emergency_contact_name = employee.emergency_contact_name;
            this.emergency_contact_no = employee.emergency_contact_no;
            this.marital_status = employee.marital_status;
            this.spouse_name = employee.spouse_name;
            this.blood_group = employee.blood_group;
            this.date_of_birth = new Date(employee.date_of_birth);
            this.country_name = employee.country_name;
            this.country_code = employee.country_code;
            this.uid_no = employee.uid_no;
            this.pan_no = employee.pan_no;
            this.voter_id = employee.voter_id;
            this.driving_license = employee.driving_license;

            this.selectedShift1 = employee.first_weekly_off ? this.week_days.find(week_day => week_day.value === employee.first_weekly_off) : null;
            this.assignFirstWeeklyOff(this.selectedShift1);
            this.fixed_shift = employee.fixed_shift ? this.shifts.find(shift => shift.id === employee.fixed_shift) : null;

        }
    });
    }


    onUpload(event:UploadEvent) {
        for(let file of event.files) {
            this.uploadedFiles.push(file);
        }

        this.messageService.add({severity: 'info', summary: 'File Uploaded', detail: ''});
    }

    imageInfos?: Observable<any>;


    fileName = '';

    selectFile(event: any): void {
        this.message = '';
        const selectedFiles = event.target.files;

        if (selectedFiles && selectedFiles.length > 0) {
            const file: File | null = selectedFiles.item(0);

            if (file) {
                this.image_file_post = file; // Assign selected file for uploading
                const reader = new FileReader();

                reader.onload = (e: any) => {
                    this.preview = e.target.result; // Set preview for the image
                    this.fileName = file.name;
                };

                reader.readAsDataURL(file);
            }
        } else {
            // If no file is selected, reset values and set default preview
            this.image_file_post = null;
            this.preview = 'assets/layout/images/profile_placeholder.jpg'; // Set default preview image
            this.fileName = '';
            console.log("No file selected.");
        }
    }

    shiftRotationCollapsed = false;
    weeklyOffCollapsed = true;

    toggleWeeklyOff() {
        this.shiftRotationCollapsed = !this.shiftRotationCollapsed;
        this.weeklyOffCollapsed = !this.weeklyOffCollapsed;
    }

    toggleShiftRotation() {
        this.weeklyOffCollapsed = !this.weeklyOffCollapsed;
        this.shiftRotationCollapsed = !this.shiftRotationCollapsed;
    }

    timeCollapsed = false;
    punchCollapsed = true;

    togglePunchSetting() {
        this.timeCollapsed = !this.timeCollapsed;
        this.punchCollapsed = !this.punchCollapsed;
    }

    toggleTimeSetting() {
        this.punchCollapsed = !this.punchCollapsed;
        this.timeCollapsed = !this.timeCollapsed;
    }

    selectedAccountType: any;
    selectedCategory: any;
    selectedJobType: any;
    selectedCompany: number | null;
    selectedLocation: number | null;
    selectedDepartment: number | null;
    selectedDesignation: number | null;
    selectedDivision: any;
    selectedSubDivision: any;
    selectedShopfloor: any;
    selectedShift: any;
    selectedShift1: number | null;
    selectedFixedShift: any;


    assignShiftId(selectedShift: any) {
        this.shift = selectedShift ? selectedShift.id : null;
        console.log("Selected Shift ID:", this.shift);
    }

    // Method to assign the selected company's ID to the 'selectedCompanyId' variable
    assignCompanyId(selectedCompany: any) {
        this.company = selectedCompany ? selectedCompany.id : null;
        console.log("Selected Company ID:", this.company);
    }

    assignLocationId(selectedLocation: any) {
        this.location = selectedLocation ? selectedLocation.id : null;
    }

    assignAccountValue(selectedAccountType) {
        this.account_type = selectedAccountType ? selectedAccountType.value: null;
    }

    assignCategoryValue(selectedCategory: any) {
        // Assign selectedCategory value after processing
        this.category = selectedCategory ? selectedCategory.value : null;

        // Reset agency selection initially
        this.agency = null;

        // Check selectedCategory value and perform actions accordingly
        switch(this.category) {
            case 'Contractor Employee':
            case 'CONTRACTOR':
                this.agencyDisabled = false;
                break;
            default:
                this.agencyDisabled = true;
                break;
        }

    }

    assignDepartmentId(selectedDepartment: any) {
        this.department = selectedDepartment ? selectedDepartment.id : null;
    }

    assignDesignationId(selectedDesignation: any) {
        this.designation = selectedDesignation ? selectedDesignation.id : null;
    }

    assignDivisionId(selectedDivision: any) {
        this.division = selectedDivision ? selectedDivision.id : null;
    }

    assignSubDivisionId(selectedSubDivision: any) {
        this.subdivision = selectedSubDivision ? selectedSubDivision.id : null;
    }

    assignShopfloorId(selectedShopfloor: any) {
        this.shopfloor = selectedShopfloor ? selectedShopfloor.id : null;
    }

    assignJobValue(selectedJobType: any) {
        this.job_type = selectedJobType ? selectedJobType.value : null;
    }

    assignMaritalValue(selectedMaritalStatus: any) {
        this.marital_status = selectedMaritalStatus ? selectedMaritalStatus.value : null;
    }

    assignCountry(selectedCountry: any) {
        this.country_name = selectedCountry ? selectedCountry.name : null;
        this.country_code = selectedCountry ? selectedCountry.code : null;
    }

    assignFirstWeeklyOff(selectedShift1: any): void {
        this.shift_1 = selectedShift1 ? selectedShift1.value : null;
    }

    assignFixedShift(selectedFixedShift: any): void {
        this.fixed_shift = selectedFixedShift ? selectedFixedShift.id : null;
    }




    employee_id: string='';
    enroll_id: string = '';
    employee_name: string = '';
    access_card_no: string = '';
    email: string = '';
    mobile_no: number = 0;
    pf_no: string = '';
    esi_no: string = '';
    insurance_no: string = '';

    bank_name: string = '';
    branch_name: string = '';
    account_no: string = '';
    account_name: string = '';
    account_type: string = '';
    ifsc_code: string = '';

    shift!: number;
    company!: number;
    location!: number;
    category: string = '';
    department!: number;
    designation!: number;
    division!: number;
    subdivision!: number;
    shopfloor!: number;
    job_type: string = '';
    date_of_joining: Date | undefined;
    date_of_leaving: Date | undefined;
    jobStatus: string = '';
    reason_for_leaving: string = '';

    emergency_contact_name: string = '';
    emergency_contact_no: number = 0;
    marital_status: string = '';
    spouse_name: string = '';
    blood_group: string = '';
    date_of_birth: Date | undefined;
    country_name: string = '';
    country_code: string = '';
    uid_no: string = '';
    pan_no: string = '';
    voter_id: string = '';
    driving_license: string = '';
    gender: string = '';
    present_address: string = '';
    permanent_address: string = '';
    shift_1!: number;

    flexi_time: boolean = false;
    consider_late_entry: boolean = true;
    consider_early_exit: boolean = true;
    consider_extra_hours_worked: boolean = true;
    consider_late_entry_on_holiday: boolean = true;
    consider_early_exit_on_holiday: boolean = true;
    consider_extra_hours_worked_on_holiday: boolean = true;
    search_next_day: boolean = false;

    fixed_shift!: number;
    auto_shift: boolean = true;
    assign_shift: boolean = false;



    resetForm() {

        this.image_file_post = null;

        this.employee_id = '';
        this.enroll_id = '';
        this.employee_name = '';
        this.access_card_no = '';
        this.email = '';
        this.mobile_no = 0;
        this.pf_no = '';
        this.esi_no = '';
        this.insurance_no = '';

        this.bank_name = '';
        this.branch_name = '';
        this.account_no = '';
        this.account_name = '';
        this.account_type = '';
        this.ifsc_code = '';

        this.category = '';
        this.selectedCategory = null;

        this.job_type = '';
        this.selectedJobType = null;

        this.date_of_joining = undefined;
        this.date_of_leaving = undefined;
        this.jobStatus = '';
        this.reason_for_leaving = '';

        this.emergency_contact_name = '';
        this.emergency_contact_no = 0;
        this.marital_status = '';
        this.spouse_name = '';
        this.blood_group = '';
        this.date_of_birth = undefined;
        this.uid_no = '';
        this.pan_no = '';
        this.voter_id = '';
        this.driving_license = '';
        this.gender = '';
        this.present_address = '';
        this.permanent_address = '';
        this.shift_1 = undefined;
        this.fixed_shift = undefined;
    }

    PostEmployee(): void {

        const formData = new FormData();

        // formData.append('profile_pic', this.image_file_post, this.image_file_post?.name || null);
        if (this.image_file_post) {
            formData.append('profile_pic', this.image_file_post, this.image_file_post.name);
          } else {
            console.log("No profile picture selected or file is invalid.");
          }
        formData.append('employee_id', this.employee_id || '');
        formData.append('employee_name', this.employee_name || '');
        formData.append('device_enroll_id', this.enroll_id || '');
        formData.append('email', this.email || '');
        // formData.append('phone_no', Number(this.mobile_no).toString());
        formData.append('pf_no', this.pf_no || '');
        formData.append('esi_no', this.esi_no || '');
        formData.append('insurance_no', this.insurance_no || '');

        formData.append('bank_name', this.bank_name);
        formData.append('bank_branch', this.branch_name);
        formData.append('bank_account_no', this.account_no);
        formData.append('bank_account_name', this.account_name);
        formData.append('bank_account_type', this.account_type);
        formData.append('ifsc_code', this.ifsc_code);

        formData.append('company', Number(this.company).toString());
        formData.append('location', Number(this.location).toString());
        formData.append('category', this.category);
        formData.append('department', Number(this.department).toString());
        formData.append('designation', Number(this.designation).toString());
        formData.append('division', Number(this.division).toString());
        // formData.append('subdivision', Number(this.subdivision).toString());
        // formData.append('shopfloor', Number(this.shopfloor).toString());
        formData.append('job_type', this.job_type);
        formData.append('job_status', this.jobStatus);
        formData.append('date_of_joining', this.datePipe.transform(this.date_of_joining, 'yyyy-MM-dd') || '');
        formData.append('date_of_leaving', this.datePipe.transform(this.date_of_leaving, 'yyyy-MM-dd') || '');
        formData.append('reason_for_leaving', this.reason_for_leaving);

        formData.append('emergency_contact_name', this.emergency_contact_name);
        // formData.append('emergency_contact_no', Number(this.emergency_contact_no).toString());
        formData.append('marital_status', this.marital_status);
        formData.append('spouse_name', this.spouse_name);
        formData.append('blood_group', this.blood_group);
        formData.append('date_of_birth', this.datePipe.transform(this.date_of_birth, 'yyyy-MM-dd') || '');
        formData.append('country_name', this.country_name);
        formData.append('country_code', this.country_code);
        formData.append('uid_no', this.uid_no);
        formData.append('pan_no', this.pan_no);
        formData.append('voter_id', this.voter_id);
        formData.append('driving_license', this.driving_license);
        formData.append('gender', this.gender);
        formData.append('present_address', this.present_address);
        formData.append('permanent_address', this.permanent_address);

        formData.append('shift', Number(this.fixed_shift).toString());
        formData.append('auto_shift', this.auto_shift ? '1' : '0');
        formData.append('first_weekly_off', this.shift_1 !== null ? this.shift_1.toString() : '');
        formData.append('flexi_time', this.flexi_time ? '1' : '0');
        formData.append('consider_late_entry', this.consider_late_entry ? '1' : '0');
        formData.append('consider_early_exit', this.consider_early_exit ? '1' : '0');
        formData.append('consider_extra_hours_worked', this.consider_extra_hours_worked ? '1' : '0');
        formData.append('consider_late_entry_on_holiday', this.consider_late_entry_on_holiday ? '1' : '0');
        formData.append('consider_early_exit_on_holiday', this.consider_early_exit_on_holiday ? '1' : '0');
        formData.append('consider_extra_hours_worked_on_holiday', this.consider_extra_hours_worked_on_holiday ? '1' : '0');

        formData.append('search_next_day', this.search_next_day ? '1' : '0');


        console.log("Form Data:", formData);

        this.service.addEmployee(formData).subscribe({
            next: (data) => {

                this.resetForm();

                this.activeStepperNumber = 0;


                console.log("Employee Added:", data);
                this.messageService.add({severity: 'success', summary: 'Employee Added', detail: 'Employee added successfully'});
            },
            error: (error) => {
                console.log("Error:", error);
                this.messageService.add({severity: 'error', summary: 'Error', detail: 'Error adding employee'});
            }
        });

    }

    updateEmployee(): void {
        const formData = new FormData();

        // formData.append('profile_pic', this.image_file_post, this.image_file_post?.name || null);
        if (this.image_file_post) {
            formData.append('profile_pic', this.image_file_post, this.image_file_post.name);
          } else {
            console.log("No profile picture selected or file is invalid.");
          }
        formData.append('employee_id', this.employee_id || '');
        formData.append('employee_name', this.employee_name || '');
        formData.append('device_enroll_id', this.enroll_id || '');
        formData.append('email', this.email || '');
        // formData.append('phone_no', Number(this.mobile_no).toString());
        formData.append('pf_no', this.pf_no || '');
        formData.append('esi_no', this.esi_no || '');
        formData.append('insurance_no', this.insurance_no || '');

        formData.append('bank_name', this.bank_name || '');
        formData.append('bank_branch', this.branch_name || '');
        formData.append('bank_account_no', this.account_no || '');
        formData.append('bank_account_name', this.account_name || '');
        formData.append('bank_account_type', this.account_type || '');  // Ensure this is a valid choice
        formData.append('ifsc_code', this.ifsc_code || '');

        // formData.append('company', Number(this.company).toString());
        // formData.append('location', Number(this.location).toString());
        formData.append('category', this.category);
        // formData.append('department', Number(this.department).toString());
        // formData.append('designation', Number(this.designation).toString());
        // formData.append('division', Number(this.division).toString());
        // formData.append('subdivision', Number(this.subdivision).toString());
        // formData.append('shopfloor', Number(this.shopfloor).toString());
        formData.append('job_type', this.job_type);
        formData.append('job_status', this.jobStatus);
        formData.append('date_of_joining', this.datePipe.transform(this.date_of_joining, 'yyyy-MM-dd') || '');
        formData.append('date_of_leaving', this.datePipe.transform(this.date_of_leaving, 'yyyy-MM-dd') || '');
        formData.append('reason_for_leaving', this.reason_for_leaving);

        formData.append('emergency_contact_name', this.emergency_contact_name);
        // formData.append('emergency_contact_no', Number(this.emergency_contact_no).toString());
        formData.append('marital_status', this.marital_status || '');
        formData.append('spouse_name', this.spouse_name);
        formData.append('blood_group', this.blood_group);
        formData.append('date_of_birth', this.datePipe.transform(this.date_of_birth, 'yyyy-MM-dd') || '');
        formData.append('country_name', this.country_name || 'India');
        formData.append('country_code', this.country_code || 'IN');
        formData.append('uid_no', this.uid_no);
        formData.append('pan_no', this.pan_no);
        formData.append('voter_id', this.voter_id);
        formData.append('driving_license', this.driving_license);
        formData.append('gender', this.gender);
        formData.append('present_address', this.present_address);
        formData.append('permanent_address', this.permanent_address);

        formData.append('shift', Number(this.fixed_shift).toString());
        formData.append('auto_shift', this.auto_shift ? '1' : '0');
        formData.append('first_weekly_off', this.shift_1 !== null ? this.shift_1.toString() : '');
        formData.append('flexi_time', this.flexi_time ? '1' : '0');
        formData.append('consider_late_entry', this.consider_late_entry ? '1' : '0');
        formData.append('consider_early_exit', this.consider_early_exit ? '1' : '0');
        formData.append('consider_extra_hours_worked', this.consider_extra_hours_worked ? '1' : '0');
        formData.append('consider_late_entry_on_holiday', this.consider_late_entry_on_holiday ? '1' : '0');
        formData.append('consider_early_exit_on_holiday', this.consider_early_exit_on_holiday ? '1' : '0');
        formData.append('consider_extra_hours_worked_on_holiday', this.consider_extra_hours_worked_on_holiday ? '1' : '0');

        formData.append('search_next_day', this.search_next_day ? '1' : '0');


        console.log("Form Data:", formData);

        this.service.updateEmployee(this.id, formData).subscribe({
            next: (data) => {

                this.resetForm();

                this.activeStepperNumber = 0;


                console.log("Employee Updated:", data);
                this.messageService.add({severity: 'success', summary: 'Employee Updated', detail: 'Employee Updated successfully'});
            },
            error: (error) => {
                console.log("Error:", error);
                this.messageService.add({severity: 'error', summary: 'Error', detail: 'Error Updating employee'});
            }
        });
    }


    private OptionsSubscription: Subscription;
    private CompaniesListSubscription: Subscription;
    private LocationsListSubscription: Subscription;
    private DepartmentsListSubscription: Subscription;
    private DesignationsListSubscription: Subscription;
    private DivisionsListSubscription: Subscription;
    private SubDivisionsListSubscription: Subscription;
    private ShopfloorsListSubscription: Subscription;

    getAllOptions(): void {

        // Use startWith to trigger an initial HTTP request
        this.OptionsSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getEmployeeFieldOptions()),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
                // Assign gender choices from the API data to the gender variable
                this.account_types = data.actions.POST.bank_account_type.choices;
                this.categories = data.actions.POST.category.choices;
                this.marital_statuses = data.actions.POST.marital_status.choices;
                this.jobTypes = data.actions.POST.job_type.choices;
                this.week_days = data.actions.POST.first_weekly_off.choices;
                console.log("week_days:", this.week_days);
        });
    }

    getShiftslist(): void {

            const params: any = {
                page: 1,
                page_size: 1000,
                sortField: '',
                ordering: '',
            };

            // Use startWith to trigger an initial HTTP request
            this.service.getShifts(params).subscribe((data: any) => {
                this.shifts = data.results;
            });
    }

    getCompaniesList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.CompaniesListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getCompanies(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.companies = data.results;
        });
    }

    getLocationsList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.LocationsListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getLocations(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.locations = data.results;
        });
    }

    getDepartmentsList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.DepartmentsListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getDepartments(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.departments = data.results;
        });
    }

    getDesignationsList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.DesignationsListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getDesignations(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.designations = data.results;
        });
    }

    getDivisionsList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.DivisionsListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getDivisions(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.divisions = data.results;
        });
    }

    getSubDivisionsList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.SubDivisionsListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getSubDivisions(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.subDivisions = data.results;
        });
    }

    getShopfloorsList(): void {

        const params: any = {
            page: 1,
            page_size: 1000,
            sortField: '',
            ordering: '',
        };

        // Use startWith to trigger an initial HTTP request
        this.ShopfloorsListSubscription = interval(100000).pipe(
            startWith(0), // emit 0 immediately
            // Use switchMap to switch to a new observable (HTTP request) each time the interval emits
            switchMap(() => this.service.getShopfloors(params)),
            // Use distinctUntilChanged to filter out repeated values
            distinctUntilChanged((prev, curr) => JSON.stringify(prev) === JSON.stringify(curr))
            ).subscribe((data: any) => {
            this.shopfloors = data.results;
        });
    }

    ngOnDestroy() {

        // Unsubscribe from the interval observable
        if (this.CompaniesListSubscription) {
            this.CompaniesListSubscription.unsubscribe();
        }

        if (this.LocationsListSubscription) {
            this.LocationsListSubscription.unsubscribe();
        }

        if (this.DepartmentsListSubscription) {
            this.DepartmentsListSubscription.unsubscribe();
        }

        if (this.DesignationsListSubscription) {
            this.DesignationsListSubscription.unsubscribe();
        }

        if (this.DivisionsListSubscription) {
            this.DivisionsListSubscription.unsubscribe();
        }

        if (this.SubDivisionsListSubscription) {
            this.SubDivisionsListSubscription.unsubscribe();
        }

        if (this.ShopfloorsListSubscription) {
            this.ShopfloorsListSubscription.unsubscribe();
        }

        if (this.OptionsSubscription) {
            this.OptionsSubscription.unsubscribe();
        }
    }

}
