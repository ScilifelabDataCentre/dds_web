const vAccountHomeApp = {
    /* Main Account Home App */
    data() {
        return {
            error_messages: [],
            account_info: null,
            account_data_loading: true
        }
    },
    methods: {
        fetchAccount() {
            axios
                .get('/user/account_methods')
                .then(response => {
                    console.log(response)
                    this.account_info = response.data
                    this.account_data_loading = false
                })
                .catch(error => {
                    this.error_messages.push('Unable to fetch account information')
                    this.account_data_loading = false
                })
        }
    }
}

const app = Vue.createApp(vAccountHomeApp)

app.component('v-account-home', {
    data() {
        return {
            new_name: {
                first: "",
                last: ""
            }
        }
    },
    computed: {
        account_info() { return this.$root.account_info }
    },
    created: function() {
        this.$root.fetchAccount();
    },
    methods: {
        submitNewName() {
            axios
                .put('/user/account_methods', {new_name: this.new_name})
                .then(response => {
                    console.log(response)
                })
                .catch(error => {
                    console.log(error)
                })
        }
    },
    template:
        /*html*/`
        <template v-if="this.$root.account_data_loading">
            <div class="spinner-grow" role="status"></div><span class="ml-3">Loading data...</span>
        </template>
        <template v-else>
            <template v-if="this.$root.any_errors">
                <template v-for="msg in this.$root.error_messages">
                    <div class="alert alert-danger" role="alert">
                    <h5 class="mt-2"><i class="far fa-exclamation-triangle mr-3"></i>{{msg}}</h5>
                    </div>
                </template>
            </template>
            <div class="row mb-3">
                <h1 class="mb-4"> Account Information </h1>
                <!-- Response messages -->
                <div id="response-container" class="alert alert-dismissible fade show my-4 d-none">
                    <span></span>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
                <!-- User account information -->
                <div class="container w-75 mx-auto bg-light mb-4 px-3 py-1">
                    <div class="row my-2">
                        <div class="col-sm">
                            <b>Username</b>
                        </div>
                        <div class="col-sm">
                            {{ account_info.username }}
                        </div>
                        <div class="col-sm"></div>
                    </div>
                    <div class="row my-2">
                        <div class="col-sm">
                            <b>Name</b>
                        </div>
                        <div class="col-sm">
                            {{ account_info.first_name }} {{ account_info.last_name }}
                        </div>
                        <div class="col-sm">
                            <button class="btn btn-sm btn-outline-info float-end px-1 mx-1 py-0" data-bs-toggle="modal" data-bs-target="#editName_modal">
                                <i class="far fa-user-edit"></i>
                            </button>
                        </div>
                    </div>
                    <template v-for="(email, i) in account_info.emails" :key="email">
                        <div class="row my-2">
                            <div class="col-sm">
                                <b v-if="i==0">Email</b>
                            </div>
                            <div class="col-sm">
                                {{ email.address }}
                                <template v-if="email.primary==true && account_info.emails.length>1">
                                    <span class="badge bg-info mx-2 px-1 me-2 ">Primary</span>
                                </template>
                            </div>
                            <div class="col-sm">
                                <template v-if="email.primary!=true && account_info.emails.length>1">
                                    <div class="dropdown">
                                        <button class="btn btn-sm btn-outline-info float-end mx-1 py-0" type="button" id="emailDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                            <i class="far fa-angle-down"></i>
                                        </button>
                                        <ul class="dropdown-menu bg-light" aria-labelledby="emailDropdown">
                                            <li>
                                                <a class="dropdown-item text-info" href="#">
                                                    <i class="far fa-thumb-tack me-2"></i>
                                                    Set as Primary
                                                </a>
                                            </li>
                                            <li>
                                                <a class="dropdown-item text-danger" href="#">
                                                    <i class="far fa-trash-can me-2"></i>
                                                    Delete
                                                </a>
                                            </li>
                                        </ul>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </template>
                    <div class="row my-2">
                        <div class="col-sm">
                            <b></b>
                        </div>
                        <div class="col-sm">
                            <button class="btn btn-sm btn-outline-info px-1 py-0" data-bs-toggle="modal" data-bs-target="#editName_modal">
                                <i class="far fa-plus me-2"></i>
                                Add New Email Address
                            </button>
                        </div>
                        <div class="col-sm"></div>
                    </div>
                    <div class="row my-2">
                        <div class="col-sm">
                            <b>Password</b>
                        </div>
                        <div class="col-sm">
                            *******
                        </div>
                        <div class="col-sm">
                            <button class="btn btn-sm btn-outline-info float-end px-1 mx-1 py-0" data-bs-toggle="modal" data-bs-target="#editName_modal">
                            <i class="far fa-lock px-1"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Change Password Modal -->
            <div class="modal fade" id="changePassword_modal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Change Password</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form method="PUT" id="change-password-form" action=""
                                class="needs-validation" novalidate>
                                <input type="hidden" name="task" value="create">
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_old">Old Password</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_new">New Password</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_repeatnew">Retype New Password</label>
                                </div>
                                <button id="newpass_submit" type="submit" class="btn btn-primary w-100 mb-3">
                                    <i class="far fa-save me-1"></i>
                                    Save
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Add Email Modal -->
            <div class="modal fade" id="addEmail_modal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Add New Email Address</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form method="POST" id="addEmail_form" action=""
                                class="needs-validation" novalidate>
                                <input type="hidden" name="task" value="create">
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" required>
                                    <label for="newuser_username">New Email Address</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" required>
                                    <label for="newuser_password">Repeat New Email Address</label>
                                </div>
                                <!--
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_password">code</label>
                                </div>
                                -->
                                <button id="newemail_submit" type="submit" class="btn btn-primary w-100 mb-3">
                                    <i class="far fa-save me-1"></i>
                                    Save
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Edit name modal-->
            <div class="modal fade" id="editName_modal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Name</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form @submit.prevent="submitNewName" method="PUT" id="editName_form" action="{{ url_for('user.account_methods') }}"
                                class="needs-validation" novalidate>
                                <div class="form-floating mb-3">
                                    <input v-model="new_name.first" type="text" class="form-control" name="firstName" id="editName_first" required>
                                    <label for="editName_first">First name</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input v-model="new_name.last" type="text" class="form-control" name="lastName" id="editName_last" required>
                                    <label for="editName_last">Last name</label>
                                </div>
                                <button type="submit" class="btn btn-primary w-100 mb-3">
                                    <i class="far fa-save me-1"></i>
                                    Save
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </template>
        `
    }
)

app.mount('#account-vue-start-point')
