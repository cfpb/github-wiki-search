module.exports = function(grunt) {

    'use strict';

    var path = require('path');

    grunt.initConfig({

        /**
         * Pull in the package.json file so we can read its metadata.
         */
        pkg: grunt.file.readJSON('package.json'),

        /**
         * Bower: https://github.com/yatskevich/grunt-bower-task
         *
         * Install Bower packages and migrate static assets.
         */
        bower: {
            install: {
                options: {
                    targetDir: './src/vendor/',
                    install: true,
                    verbose: true,
                    cleanBowerDir: true,
                    cleanTargetDir: true,
                    layout: function(type, component) {
                        if (type === 'img') {
                            return path.join('../static/img');
                        } else if (type === 'fonts') {
                            return path.join('../static/fonts');
                        } else {
                            return path.join(component);
                        }
                    }
                }
            }
        },

        /**
         * Concat: https://github.com/gruntjs/grunt-contrib-concat
         *
         * Concatenate cf-* LESS files prior to compiling them.
         */
        concat: {
            'cf-less': {
                src: [
                    'src/vendor/cf-*/*.less'
                ],
                dest: 'src/vendor/cf-concat/cf.less'
            }
        },

        /**
         * LESS: https://github.com/gruntjs/grunt-contrib-less
         *
         * Compile LESS files to CSS.
         */
        less: {
            main: {
                options: {
                    paths: grunt.file.expand('src/vendor/**/')
                },
                files: {
                    'src/static/css/main.css': ['src/static/css/main.less']
                }
            }
        },

        /**
         * Autoprefixer: https://github.com/nDmitry/grunt-autoprefixer
         *
         * Parse CSS and add vendor-prefixed CSS properties using the Can I Use database.
         */
        autoprefixer: {
            options: {
                // Options we might want to enable in the future.
                diff: false,
                map: false
            },
            multiple_files: {
                // Prefix all CSS files found in `src/static/css` and overwrite.
                expand: true,
                src: 'src/static/css/*.css'
            }
        },

        /**
         * Uglify: https://github.com/gruntjs/grunt-contrib-uglify
         *
         * Minify JS files.
         * Make sure to add any other JS libraries/files you'll be using.
         * You can exclude files with the ! pattern.
         */
        uglify: {
            options: {
                sourceMap: true,
                sourceMapUrl: '/static/js/main.min.js',
                beautify: false,
                drop_console: true
            },
            bodyScripts: {
                src: [
                    'src/vendor/jquery/jquery.js',
                    'src/vendor/jquery.easing/jquery.easing.js',
                    'src/static/js/jquery-hashchange.js',
                    'src/vendor/typeahead.js/typeahead.bundle.js',
                    'src/vendor/cf-*/*.js',
                    'src/static/js/jquery.custom-input.js',
                    'src/static/js/jquery.custom-select.js',
                    'src/static/js/custom-select.js',
                    'src/static/js/query.js',
                    'src/static/js/app.js'
                ],
                dest: 'src/static/js/main.min.js'
            }
        },

        /**
         * CSS Min: https://github.com/gruntjs/grunt-contrib-cssmin
         *
         * Minify CSS and optionally rewrite asset paths.
         */
        cssmin: {
            combine: {
                options: {
                    //root: '/src/'
                },
                files: {
                    'src/static/css/main.min.css': ['src/static/css/main.css'],
                    'src/static/css/fonts.min.css': ['src/static/css/fonts.css'],
                }
            }
        },

        /**
         * Clean: https://github.com/gruntjs/grunt-contrib-clean
         *
         * Clear files and folders.
         */
        clean: {
            bowerDir: ['bower_components'],
            dist: ['dist/**/*', '!dist/.git/']
        },

        /**
         * Copy: https://github.com/gruntjs/grunt-contrib-copy
         *
         * Copy files and folders.
         */
        copy: {
            dist: {
                files: [{
                    expand: true,
                    cwd: 'src/',
                    src: [
                        "*.xml",
                        'index.html',
                        'static-test.html',
                        //simplify debugging
                        'static/js/app.js',
                        // Only include minified assets in css/ and js/
                        'static/css/*.min.css',
                        'static/js/html5shiv-printshiv.js',
                        'static/js/*.min.js',
                        'static/js/*.min.js.map',
                        'static/fonts/**',
                        'static/img/**'
                    ],
                    dest: 'dist/'
                }]
            },
            vendor: {
                files: [{
                    expand: true,
                    cwd: 'src/',
                    src: [
                        // Only include vendor files that we use independently
                        'vendor/html5shiv/html5shiv-printshiv.min.js',
                        'vendor/box-sizing-polyfill/boxsizing.htc'
                    ],
                    // Place them in static/
                    dest: 'dist/static/'
                }]
            }
        },

        /**
         * grunt-gh-pages: https://github.com/tschaub/grunt-gh-pages
         *
         * Use Grunt to push to your gh-pages branch hosted on GitHub or any other branch anywhere else
         */
        'gh-pages': {
            options: {
                base: 'dist'
            },
            src: ['**']
        },

        /**
         * JSHint: https://github.com/gruntjs/grunt-contrib-jshint
         *
         * Validate files with JSHint.
         * Below are options that conform to idiomatic.js standards.
         * Feel free to add/remove your favorites: http://www.jshint.com/docs/#options
         */
        jshint: {
            options: {
                camelcase: false,
                curly: true,
                forin: true,
                immed: true,
                latedef: true,
                newcap: true,
                noarg: true,
                quotmark: true,
                sub: true,
                boss: true,
                strict: true,
                evil: true,
                eqnull: true,
                browser: true,
                plusplus: false,
                globals: {
                    jQuery: true,
                    $: true,
                    module: true,
                    require: true,
                    define: true,
                    console: true,
                    EventEmitter: true
                }
            },
            all: ['src/static/js/main.min.js']
        },

        /**
         * Watch: https://github.com/gruntjs/grunt-contrib-connect
         *
         * Start a static web server.
         */
        connect: {
            server: {
                options: {
                    base: 'dist'
                },
            },
        },

        /**
         * Watch: https://github.com/gruntjs/grunt-contrib-watch
         *
         * Run predefined tasks whenever watched file patterns are added, changed or deleted.
         * Add files to monitor below.
         */
        watch: {
            src: {
                options: {
                    livereload: true
                },
                files: [
                    'Gruntfile.js',
                    'src/index.html',
                    'src/static/css/*.less',
                    'src/static/js/query_variables.js',
                    'src/static/js/expandable.js',
                    'src/static/js/app.js',
                    'src/static/js/query.js'
                ],
                tasks: ['default', 'dist']
            }
        }
    });

    /**
     * The above tasks are loaded here.
     */
    grunt.loadNpmTasks('grunt-autoprefixer');
    grunt.loadNpmTasks('grunt-bower-task');
    grunt.loadNpmTasks('grunt-contrib-clean');
    grunt.loadNpmTasks('grunt-contrib-concat');
    grunt.loadNpmTasks('grunt-contrib-connect');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-contrib-cssmin');
    grunt.loadNpmTasks('grunt-contrib-jshint');
    grunt.loadNpmTasks('grunt-contrib-less');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-gh-pages');
    grunt.loadNpmTasks('grunt-shell');

    /**
     * Create custom task aliases and combinations
     */
    grunt.registerTask('vendor', ['clean:bowerDir', 'bower:install', 'concat:cf-less']);
    grunt.registerTask('default', ['less', 'autoprefixer', 'cssmin', 'uglify']);
    grunt.registerTask('dist', ['clean:dist', 'copy:dist', 'copy:vendor']);

    /**
     * Start a connect server and watch for changes
     */
    grunt.registerTask('serve', [
        'dist',
        'connect',
        'watch'
    ]);

};