const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const Dotenv = require('dotenv-webpack');
const paths = require('./paths');
const apiMocker = require('mocker-api');
const path = require('path');
const httpProxy = require('http-proxy');

pdserverHost = process.env.PDSERVER_HOST;

module.exports = {
    mode: 'development',
    devtool: 'cheap-module-source-map',
    devServer: {
        onListening: function() {
            httpProxy.createServer({
                target: `ws://${pdserverHost}:7001`,
                ws: true
            }).listen(7001);      
        },
        hot: true,
        static: paths.outputPath,
        port: 3000,
        proxy: {
            '/rpc': `http://${pdserverHost}:7000`,
        },
        open: true,
        /*overlay: {
            errors: true,
            warnings: true,
        },*/
        compress: true,
        historyApiFallback: true
    },
    module: {
        rules: [{
            test: /\.js$/,
            enforce: 'pre',
            exclude: /node_modules/,
            loader: 'eslint-loader',
            options: {
                cache: false,
                configFile: './.eslintrc.js',
                emitWarning: true,
                // Fail only on errors
                failOnWarning: false,
                failOnError: false,
                // Toggle autofix
                fix: false,
                formatter: require('eslint/lib/cli-engine/formatters/stylish')
            }
        }]
    },
    output: {
        path: paths.outputPath,
        filename: 'js/[name].js',
        chunkFilename: 'js/[name].js'
    },
    plugins: [
        new Dotenv({
            path: paths.envDevPath, // Path to .env.development file
            expand: true 
        }),
        new Dotenv({
            path: paths.envPath, // Path to .env file 
            expand: true
        }),
        new MiniCssExtractPlugin({
            filename: 'css/[name].css',
            chunkFilename: 'css/[id].css'
        }),
        new webpack.HotModuleReplacementPlugin()
    ],
    optimization: {
        splitChunks: {
            chunks: 'all'
        }
    }
};
