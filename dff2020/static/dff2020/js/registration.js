new Vue({
    el: '#movies-app',
    data: {
        movies: [],
        per_movie: 299
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
            this.movies.push({ name: '', director: '', runtime: '' });
        },
        remove_movie(index) {
            console.log(index, 'deleted');
            this.movies.splice(index, 1);
        }
    }
})