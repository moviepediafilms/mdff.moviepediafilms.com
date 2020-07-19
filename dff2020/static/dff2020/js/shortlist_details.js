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
        rated_movie: !locked,
        quiz_over: quiz_over,
    },
    methods: {
        btn_action() {
            if (this.logged_in) {
                if (this.rated_movie) {
                    if (this.quiz_over) {
                        // movie to leaderboard page
                        window.location.replace(`/shortlist/${shortlist_id}/result`);
                    } else {
                        $('#model-quiz').modal('show')
                    }
                }
                else {
                    $('#model-rating').modal('show')
                }
            }
            else
                $('#model-login').modal('show')
        }
    },
    computed: {
        btn_txt() {
            if (this.quiz_over)
                return "Leaderboard"
            else
                return "Take The Quiz"
        },
        p_text() {
            if (!this.rated_movie)
                return "Rate to Unlock Scores and Claim Your Prize"
            if (this.quiz_over)
                return "Check leaderboard to view your score"
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
            rating: 5,
            review: "",
        }
    },
    computed: {
        rating_text() {
            return {
                0: "😫",
                1: "😖",
                2: "🥱",
                3: "😕",
                4: "😐",
                5: "🙂",
                6: "😊",
                7: "😀",
                8: "🤩",
                9: "😍",
                10: "🤯",
            }[this.form.rating]
        }
    },
    methods: {
        show_quiz() {
            $('#model-rating').modal('hide')
            $('#model-quiz').modal('show')
            $('#model-quiz').on('hidden.bs.modal', function () {
                window.location.reload();
            });
        },
        rate() {
            this.loading = true;
            this.form.error = ""
            var data = new FormData()
            var app = this
            data.append('review', this.form.review)
            data.append('rating', this.form.rating)
            axios.post(`/api/rate/${shortlist_id}`, data, { headers: { "X-CSRFToken": csrf } }).then(response => {
                console.log(response)
                if (response.data.success) {
                    app.show_quiz()
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

var quiz_app = new Vue({
    el: '#quiz-model-app',
    data: {
        quiz_started: false,
        quiz_start_time: null,
        question: {},
        question_count: 0,
        secs_left: -1,
        error: "",
        selected_option: {},
        correct_option_was: null,
        sending: false,
    },
    watch: {
        quiz_ended() {
            if (this.quiz_ended)
                setTimeout(() => {
                    window.location.reload()
                }, 2000)
        }
    },
    computed: {
        quiz_ended() {
            return this.quiz_started && (this.secs_left <= 0 || this.question_count == 3)
        },
        title() {
            if (!this.quiz_started)
                return "Quiz"
            else if (this.quiz_ended)
                return "Quiz Completed"
            else {
                var hours = parseInt(this.secs_left / 3600)
                var minutes = parseInt((this.secs_left - hours * 3600) / 60)
                var secs = this.secs_left - hours * 3600 - minutes * 60
                if (hours)
                    return String(hours).padStart(2, 0) + ":" + String(minutes).padStart(2, 0) + ":" + String(secs).padStart(2, '0')
                else
                    return String(minutes).padStart(2, 0) + ":" + String(secs).padStart(2, '0')
            }
        }
    },
    methods: {
        start_quiz() {
            var vm = this;
            axios.get('/api/quiz/start/' + shortlist_id)
                .then(response => {
                    console.log(response)
                    if (response.data.success) {
                        vm.question = response.data.question
                        vm.question_count = response.data.question_count
                        vm.quiz_started = true
                        vm.secs_left = parseInt((moment(response.data.start_time).add(response.data.quiz_time_limit, "seconds") - moment()) / 1000)
                        vm.timer()
                    } else {
                        vm.error = response.data.error
                    }
                })
                .catch(error => {
                    console.log(error)
                    vm.error = "Error occured"
                })
        },
        submit_question(option) {
            var vm = this
            vm.selected_option = option
            vm.sending = true
            axios.get(`/api/quiz/${shortlist_id}/${this.question.id}/${option.id}`)
                .then(response => {
                    vm.sending = false;
                    if (response.data.success) {
                        if (response.data.previous_correct_answer) {
                            option.was_correct = true
                        }
                        setTimeout(() => {
                            vm.selected_option = {}
                            vm.question = response.data.question;
                            vm.question_count = response.data.question_count;
                        }, 1000)
                    }
                    else {
                        vm.error = response.data.error
                    }
                }).catch(error => {
                    console.log(error)
                    vm.error = "Error occured"
                })
        },
        timer() {
            if (this.secs_left > 0) {
                setTimeout(() => {
                    this.secs_left -= 1
                    this.timer()
                }, 1000)
            }
        }
    }
})