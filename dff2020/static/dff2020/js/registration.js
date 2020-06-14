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
        rzp_response_handler(rzp_response) {
            console.log(rzp_response);
            if (rzp_response.error) {
                console.log("Payment failed!")
                window.location = `/payment/error?description=${rzp_response.description}&order_id=${rzp_response.meta.order_id}&payment_id=${rzp_response.meta.payment_id}`;
            }
            else {
                this.lock_input = true
                console.log("Payment success! call server for ")
                this.message = "verifying payment! "
                axios.post('/verify_payment', rzp_response, { headers: { "X-CSRFToken": this.csrf } })
                    .then(response => {
                        this.lock_input = false
                        console.log(response);
                        if (response.data.success) {
                            this.message = response.data.message
                            // redirect user
                            window.location.href = `/payment/success?description=Payment Successful&order_id=${rzp_response.razorpay_order_id}&payment_id=${rzp_response.razorpay_payment_id}`;
                        } else {
                            this.error = response.data.error
                            window.location = `/payment/error?description=${response.data.error}&order_id=${rzp_response.razorpay_order_id}&payment_id=${rzp_response.razorpay_payment_id}`;
                        }
                    }, error => {
                        this.lock_input = false
                        this.error = 'Payment verification failed!'
                        console.log(error);
                        window.location.href = `/payment/error?description=${this.error}&order_id=${rzp_response.razorpay_order_id}&payment_id=${rzp_response.razorpay_payment_id}`;
                    })
            }
        },
        validate_input() {
            var errors = 0
            this.movies.forEach(movie => {
                movie.name.error = !movie.name.value
                movie.director.error = !movie.director.value
                if (movie.runtime.value) {
                    var runtime = parseInt(movie.runtime.value)
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
                            this.csrf = response.data.csrf
                            var rzp_options = {
                                "key": "rzp_test_Zhdtys04NuaToI", // Enter the Key ID generated from the Dashboard
                                "amount": response.data.amount, // Amount is in currency subunits. Default currency is INR. Hence, 50000 refers to 50000 paise
                                "currency": "INR",
                                "name": "Moviepedia Films",
                                "order_id": response.data.order_id, //This is a sample Order ID. Pass the `id` obtained in the response of Step 1
                                "handler": this.rzp_response_handler,
                                "prefill": {
                                    "name": response.data.name,
                                    "email": response.data.email,
                                }
                            };
                            console.log("opening razorpay")
                            new Razorpay(rzp_options).open();
                        }
                    }, error => {
                        this.lock_input = false
                        console.log(error)
                    })
            }
        }
    }
})