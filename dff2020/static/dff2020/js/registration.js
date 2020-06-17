new Vue({
    el: '#movies-app',
    data: {
        movies: [],
        per_movie: 299,
        error: '',
        message: '',
        csrf: '',
        lock_input: false
    },
    mounted() {
        this.add_movie();
    },
    computed: {
        amount() {
            return this.movies.length * 299;
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