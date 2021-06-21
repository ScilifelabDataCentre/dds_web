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
            this.account_info = {
                'username': 'vue_test_user1',
                'emails':
                    [ {'address': 'test@example.com', 'primary': true} ],
                    // {'address':'test2@example.com', 'primary': false} ],
                'permissions': 'example_permission',
                'first_name': 'little_test',
                'last_name': 'testsson'
            };
            setTimeout(
                () => {
                    this.account_data_loading = false;
                },
                1000
            )

            /*
            // This is what we really should be using
            axios
                .get('/api/v1/account_info')
                .then(response => {
                    this.account_info = response.data.account_info
                    this.account_data_loading = false
                })
                .catch(error => {
                    this.error_messages.push('Unable to fetch account information')
                    this.account_data_loading = false
                })
            */
        //    axios.get('/api/account', {this.$root.account_info. username})
        }
    }
}

const app = Vue.createApp(vAccountHomeApp)

app.component('v-account-home', {
    data() {
        return {
            edit_mode: false
        }
    },
    computed: {
        account_info() { return this.$root.account_info }
    },
    created: function() {
        this.$root.fetchAccount();
    },
    methods: {
        toggleEdit() {
            this.edit_mode = !this.edit_mode
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
            <div class="modal fade" id="changePassword_modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Change Password</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form method="POST" id="change-password-form" action=""
                                class="needs-validation" novalidate>
                                <input type="hidden" name="task" value="create">
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" required>
                                    <label for="newuser_username">Old Password</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newuser_password">New Password</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_password">Retype New Password</label>
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
            <div class="modal fade" id="addEmail_modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Add New Email Address</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form method="POST" id="add-email-form" action=""
                                class="needs-validation" novalidate>
                                <input type="hidden" name="task" value="create">
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" required>
                                    <label for="newuser_username">New Email Address</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newuser_password">Repeat New Email Address</label>
                                </div>
                                <!--
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_password">code</label>
                                </div>
                                -->
                                <button id="newpass_submit" type="submit" class="btn btn-primary w-100 mb-3">
                                    <i class="far fa-save me-1"></i>
                                    Save
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal fade" id="editName_modal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Name</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form method="POST" id="edit-name-form" action=""
                                class="needs-validation" novalidate>
                                <input type="hidden" name="task" value="create">
                                <div class="form-floating mb-3">
                                    <input type="text" class="form-control" required>
                                    <label for="newuser_username">New First Name</label>
                                </div>
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newuser_password">Nex Last Name</label>
                                </div>
                                <!--
                                <div class="form-floating mb-3">
                                    <input type="password" class="form-control" required>
                                    <label for="newpass_password">code</label>
                                </div>
                                -->
                                <button id="newpass_submit" type="submit" class="btn btn-primary w-100 mb-3">
                                    <i class="far fa-save me-1"></i>
                                    Save
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mb-3">
                <h1 class="mb-4"> Account Information </h1>
                <div class="container w-75 mx-auto mb-4">
                    <div class="bg-light px-2 py-1">
                        <table class="table table-hover">
                            <tbody>
                                <tr>
                                    <th>  Username </th>
                                    <td> {{ account_info.username }} </td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <th>  Permissions </th>
                                    <td> {{ account_info.permissions }} </td>
                                    <td></td>
                                </tr>
                                <tr>
                                    <th>  Name </th>
                                    <td> {{ account_info.first_name }} {{ account_info.last_name }} </td>
                                    <td>
                                        <button v-if="!edit_mode" class="btn btn-sm btn-outline-info float-end py-0" id="editName" data-bs-toggle="modal" data-bs-target="#editName_modal">
                                            <i class="far fa-user-edit"></i>
                                        </button>
                                    </td>
                                </tr>
                                <template v-for="(email, i) in account_info.emails" :key="email">
                                    <tr>
                                        <th v-if="i==0">
                                            Email
                                        </th>
                                        <th v-else>
                                        </th>
                                        <td>
                                            {{email.address}}
                                            <template v-if="email.primary==true && account_info.emails.length>1">
                                                <span v-if="!edit_mode" class="badge bg-info mx-2 px-1 py-1 ">Primary</span>
                                            </template>
                                        </td>
                                        <td>
                                            <button v-if="!edit_mode && account_info.emails.length>1" class="btn btn-sm btn-outline-danger float-end mx-1 py-0" :disabled="email.primary">
                                                <i class="far fa-trash-can"></i>
                                            </button>
                                            <div v-if="edit_mode" class="float-end">
                                                <label class="btn btn-sm btn-outline-info mx-2 px-1 py-0">
                                                    <input v-if="edit_mode" class="form-check-input" type="radio" name="option_primary">
                                                    Primary
                                                </label>
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                    <div class="text-end">
                        <button v-if="!edit_mode" type="button" class="btn btn-sm end btn-outline-info my-2 mx-1" id="editPassword" data-bs-toggle="modal" data-bs-target="#changePassword_modal">
                        <i class="far fa-lock me-2"></i>
                        Change password
                        </button>
                        <button v-if="!edit_mode" type="button" class="btn btn-sm end btn-outline-info my-2 mx-1" id="addEmail" data-bs-toggle="modal" data-bs-target="#addEmail_modal">
                        <i class="far fa-envelope me-2"></i>
                        Add New Email Address
                        </button>
                        <template v-if="account_info.emails.length>1">
                        <button type="button" class="btn btn-sm btn-outline-info my-2 mx-1" id="editFields" @click="toggleEdit" disabled>
                            <span v-if="!edit_mode" id="editTag">
                            <i class="far fa-inbox me-2"></i>
                            Change Primary Email
                            </span>
                            <span v-if="edit_mode" id="cancelTag">
                            <i class="far fa-chevron-circle-left me-2" ></i>
                                Cancel
                            </span>
                        </button>
                        <button v-if="edit_mode" type="button" class="btn btn-sm btn-outline-success my-2 mx-1" id="editFields" @click="toggleEdit">
                            <span  id="cancelTag">
                            <i class="far fa-check-circle me-2" ></i>
                                save
                            </span>
                        </button>
                        </template>
                    </div>
                </div>
            </div>
        </template>
        `
    }
)

app.mount('#account-vue-start-point')
