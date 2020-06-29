var app = new Vue({
    el: '#movies-app',
    data: {
        movies: [],
        per_movie: 299,
        error: '',
        message: '',
        csrf: '',
        lock_input: false,
        extra_fees: 0,
    },
    mounted() {
        var late_start = moment.tz("2020-07-01T00:00:00", "Asia/Kolkata");
        console.log(late_start.format())
        console.log(moment(user_joining_date).format())
        console.log(moment(user_joining_date).tz("Asia/Kolkata").format())
        if (moment(user_joining_date).isAfter(late_start)) {
            this.extra_fees = 99
        }
        console.log("extra_fees", this.extra_fees)
        this.add_movie();
    },
    computed: {
        amount() {
            return this.movies.length * 299 + this.extra_fees;
        }
    },
    methods: {
        add_movie() {
            this.movies.push({
                name: { value: '', error: false },
                director: { value: '', error: false },
                runtime: { value: '', error: false },
                link: { value: '', error: false },
                synopsis: { value: '', error: false }
            });
        },
        remove_movie(index) {
            this.movies.splice(index, 1);
        },
        validate_input() {
            var errors = 0
            this.movies.forEach(movie => {
                movie.name.error = !movie.name.value
                movie.director.error = !movie.director.value
                if (movie.runtime.value) {
                    var runtime = parseFloat(movie.runtime.value)
                    movie.runtime.error = !(runtime > 0 && runtime <= 30)
                } else {
                    movie.runtime.error = true
                }
                movie.link.error = !this.valid_URL(movie.link.value)
                if (movie.link.error || movie.runtime.error || movie.director.error || movie.name.error)
                    errors += 1
            })
            if (errors > 0)
                this.error = errors.length == 1 ? "Invalid value" : "Invalid values"
            return errors == 0
        },
        valid_URL(str) {
            var pattern = new RegExp('^(https?:\\/\\/)?' + // protocol
                '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|' + // domain name
                '((\\d{1,3}\\.){3}\\d{1,3}))' + // OR ip (v4) address
                '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*' + // port and path
                '(\\?[;&a-z\\d%_.~+=-]*)?' + // query string
                '(\\#[-a-z\\d_]*)?$', 'i'); // fragment locator
            return !!pattern.test(str);
        },
        create_order() {
            this.lock_input = true
            this.error = ''
            if (this.validate_input()) {
                var movies = []
                this.movies.forEach(movie => {
                    movies.push({
                        name: movie.name.value,
                        director: movie.director.value,
                        runtime: movie.runtime.value,
                        synopsis: movie.synopsis.value,
                        link: movie.link.value
                    })
                })
                data = { 'entries': movies }
                console.log("creating order", data)
                var csrfmiddlewaretoken = this.$el.querySelector('input[name="csrfmiddlewaretoken"]')
                axios.post('/registration', data, { headers: { "X-CSRFToken": csrfmiddlewaretoken.value } })
                    .then(response => {
                        this.lock_input = false
                        if (!response.data.success) {
                            this.error = response.data.error
                            console.log("creating order failed")
                        }
                        else {
                            this.lock_input = true
                            this.error = ""
                            this.message = response.data.message
                            console.log("creating order success")
                            window.location = '/submissions'
                        }
                    }, error => {
                        this.lock_input = false
                        console.log(error)
                    })
            }
        }
    }
})

var steps = new Vue({
    el: '#steps',
    data: {
        steps: [
            {
                id: 1,
                name: "Registrations Start",
                date: "June 20th",
                activate_on: moment.tz('Jun 20 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 2,
                name: "Registrations End",
                desc: "No new users will be able to create their accounts on the website after this",
                date: "June 26th",
                activate_on: moment('Jun 27 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 3,
                name: "Registrations Extended",
                desc: "Free registrations can now be done till 30th June, after which a late registration fee of ₹99 will be charged",
                date: "June 30th",
                activate_on: moment('Jun 27 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 4,
                name: "Late Registrations & Submissions Closed",
                desc: "No Submissions and/or registrations will be accepted after 10th July 11:59 PM",
                date: "July 10th",
                activate_on: moment('Jul 01 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 5,
                name: "Screening of top 10 Films",
                desc: "Top 10 entries hand-picked by our jury of judges will be screened across platforms of Moviepedia",
                date: "July 24th - August 1st",
                activate_on: moment('Jul 10 2020', "MMM DD YYYY", "Asia/Kolkata")
            },
            {
                id: 6,
                name: "Results",
                desc: "Winners will be announced on the final day of the Film Festival",
                date: "August 2nd",
                activate_on: moment('Aug 02 2020', "MMM DD YYYY", "Asia/Kolkata")
            }]
    },
    mounted() {
        $('.stepper').mdbStepper();
    },
    computed: {
        active_step_id() {
            var today = moment().tz("Asia/Kolkata")
            var active_step_id = 1
            this.steps.forEach(step => {
                if (today.isAfter(step.activate_on)) {
                    active_step_id = step.id
                }
            })
            return active_step_id;
        }
    }
})
