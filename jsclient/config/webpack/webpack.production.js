const webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserPlugin = require('terser-webpack-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const Dotenv = require('dotenv-webpack');
const paths = require('./paths');

module.exports = {
    mode: 'production',
    devtool: 'source-map',
    output: {
        path: paths.outputPath,
        filename: 'js/[name]-[contenthash:8].js',
        chunkFilename: 'js/[name]-[contenthash:8].js'
    },
    plugins: [
        new webpack.ids.HashedModuleIdsPlugin(), // so that file hashes don't change unexpectedly
        new CleanWebpackPlugin(),
        new Dotenv({
            path: paths.envProdPath, // Path to .env.production file
            expand: true
        }),
        new Dotenv({
            path: paths.envPath, // Path to .env file
            expand: true
        }),
        new MiniCssExtractPlugin({
            filename: 'css/[name]-[contenthash:8].css',
            chunkFilename: 'css/[id]-[contenthash:8].css'
        })
    ],
    optimization: {
        runtimeChunk: 'single',
        splitChunks: {
            chunks: 'all',
            maxInitialRequests: Infinity,
            minSize: 30000,
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name(module) {
                        // With webpack5, the test condition above does not seem to preclude
                        // this function being called with modules that are not from node_modules

                        // get the name. E.g. node_modules/packageName/not/this/part.js
                        // or node_modules/packageName
                        const match = module.context.match(
                            /[\\/]node_modules[\\/](.*?)([\\/]|$)/
                        );

                        if(match) {
                            const packageName = match[1];
                            // npm package names are URL-safe, but some servers don't like @ symbols
                            return `vendor.${packageName.replace('@', '')}`;
                        } else {
                            return false;
                        }
                    }
                },
                default: false
            }
        },
        minimizer: [new TerserPlugin({}), new CssMinimizerPlugin({})]
    }
};
