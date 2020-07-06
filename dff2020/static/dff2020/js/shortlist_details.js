var barColorJury = "#00C851";
var barColorAudience = "#ffc221";

var onupdate = function (from, to, percent) {
    if (!locked)
        $(this.el).find('.percent').text(Math.round(percent) / 10 + "/10");
}
$(function () {
    $('#chart-jury').easyPieChart({
        barColor: barColorJury,
        trackColor: "#212121",
        scaleLength: 0,
        lineWidth: 7,
        lineCap: "round",
        onStep: onupdate
    });
    $('#chart-audience').easyPieChart({
        barColor: barColorAudience,
        trackColor: "#212121",
        scaleLength: 0,
        lineWidth: 7,
        lineCap: "round",
        onStep: onupdate
    });
});


var signin = new Vue({
    el: '#login-model-app',
    data: {
        form: {
            email: "",
            password: "",
            error: "",
        }
    },
    computed: {
    },
    methods: {
        open_signup() {
            $('#model-login').modal('hide')
            $('#model-signup').modal('show')
        },
        show_rating() {
            $('#model-login').modal('hide')
            $('#model-rating').modal('show')
        },
        signin() {
            var data = new FormData()
            var app = this
            data.append('email', this.form.email)
            data.append('password', this.form.password)
            axios.post('/api/login', data, { headers: { "X-CSRFToken": csrf } }).then(response => {
                console.log(response)
                if (response && !response.data.success) {
                    app.form.error = response.data.error
                }
                if (response && response.data.success) {
                    // show the rating model
                    csrf = response.data.csrf
                    button_app.$data.logged_in = true
                    app.show_rating()
                }
            }).catch(error => {
                console.log(error)
            })
        }
    }
})
var signup = new Vue({
    el: '#signup-model-app',
    data: {
        form: {
            error: "",
            name: { value: "", error: "" },
            email: { value: "", error: "" },
            password: { value: "", error: "" },
            cnf_password: { value: "", error: "" }
        }
    },
    computed: {
    },
    methods: {
        open_signin() {
            $('#model-signup').modal('hide')
            $('#model-login').modal('show')
        },
        is_form_valid() {
            console.log(this.form.password.value)
            console.log(this.form.cnf_password.value)
            if (this.form.password.value != this.form.cnf_password.value) {
                this.form.cnf_password.error = "Passwords should match!"
                return false
            } else {
                this.form.cnf_password.error = ""
            }
            return true
        },
        show_rating() {
            $('#model-signup').modal('hide')
            $('#model-rating').modal('show')
        },
        signup() {
            if (this.is_form_valid()) {
                var data = new FormData()
                var app = this
                data.append('name', this.form.name.value)
                data.append('email', this.form.email.value)
                data.append('password', this.form.password.value)
                data.append('cnf_password', this.form.cnf_password.value)
                data.append('agree', true)
                axios.post('/api/signup/quick', data, { headers: { "X-CSRFToken": csrf } }).then(response => {
                    console.log(response)
                    if (response.data && !response.data.success) {
                        app.form.error = response.data.error
                    }
                    if (response.data && response.data.success) {
                        // show the rating model
                        csrf = response.data.csrf
                        button_app.$data.logged_in = true
                        app.show_rating()
                    }
                }).catch(error => {
                    console.log(error)
                })
            }
        }
    }
})

var button_app = new Vue({
    el: '#center-button-app',
    data: {
        logged_in: logged_in,
        rated_movie: !locked
    },
    methods: {
        btn_action() {
            if (this.logged_in) {
                if (this.rated_movie)
                    $('#model-quiz').modal('show')
                else
                    $('#model-rating').modal('show')
            }
            else
                $('#model-login').modal('show')
        }
    },
    computed: {
        btn_txt() {
            if (!this.rated_movie)
                return "Rate this movie"
            return "Take a quiz"
        },
        p_text() {
            if (!this.rated_movie)
                return "Rate to unlock jury, audence ratings and claim your prize"
            return "Take a quiz about this movie and claim your prize"
        }
    },
})

var rating_app = new Vue({
    el: '#rating-model-app',
    data: {
        loading: false,
        form: {
            error: '',
            rating: "",
            review: "",
        }
    },
    methods: {
        rate() {
            this.loading = true;
            this.form.error = ""
            var data = new FormData()
            var app = this
            data.append('review', this.form.review)
            data.append('rating', this.form.rating)
            axios.post('/api/rate', data, { headers: { "X-CSRFToken": csrf } }).then(response => {
                console.log(response)
                if (response.data.success) {
                    window.location.reload();
                } else {
                    app.form.error = response.data.error
                    this.loading = false;
                    if (response.data.reload) {
                        setTimeout(function () {
                            window.location.reload();
                        }, 2000);
                    }
                }
            }).catch(error => {
                console.log(error)
                this.loading = false;
            })
        },
    }
})