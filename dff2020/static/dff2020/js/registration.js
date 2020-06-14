new Vue({
    el: '#movies-app',
    data: {
        movies: [],
        per_movie: 299,
        error: '',
        message: '',
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
            this.movies.push({ name: '', director: '', runtime: '', link: '', synopsis: '' });
        },
        remove_movie(index) {
            console.log(index, 'deleted');
            this.movies.splice(index, 1);
        },
        rzp_response_handler(response) {
            console.log(response);
            if (response.error)
                console.log("Payment failed!")
            else
                console.log("Payment success! call server for ")
            axios.post('/verify_payment', response).then(response => {
                console.log(response);
            }, error => {
                console.log(error);
            })
        },
        create_order() {
            this.error = ''
            data = { 'entries': this.movies }
            console.log("creating order", data)
            var csrfmiddlewaretoken = this.$el.querySelector('input[name="csrfmiddlewaretoken"]')
            axios.post('/registration', data, { headers: { "X-CSRFToken": csrfmiddlewaretoken.value } })
                .then(response => {

                    if (!response.data.success) {
                        this.error = response.data.error
                        console.log("creating order failed")
                    }
                    else {
                        console.log("creating order success")
                        this.message = response.data.message
                        this.error = ""
                        var rzp_options = {
                            "key": "rzp_test_Zhdtys04NuaToI", // Enter the Key ID generated from the Dashboard
                            "amount": response.data.amount, // Amount is in currency subunits. Default currency is INR. Hence, 50000 refers to 50000 paise
                            "currency": "INR",
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
                    console.log(error)
                })
        }
    }
})