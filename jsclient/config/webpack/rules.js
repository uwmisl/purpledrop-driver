const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const postcssNormalize = require('postcss-normalize');
const imageInlineSizeLimit = 10000;
const fontInlineSizeLimit = 10000;

module.exports = [
    {
        test: /\.(ttf|otf|eot|woff(2)?)(\?[a-z0-9]+)?$/,
        loader: 'url-loader',
        options: {
            limit: fontInlineSizeLimit,
            name: 'fonts/[name].[ext]',
        }
    },
    {
        test: /\.(sa|sc|c)ss$/,
        use: [
            {
                loader: MiniCssExtractPlugin.loader,
            },
            {
                loader: 'css-loader'
            },
            {
                loader: 'postcss-loader',
                options: {
                    postcssOptions: {
                        ident: 'postcss',
                        plugins: () => [
                            require('postcss-flexbugs-fixes'),
                            require('postcss-preset-env')({
                                autoprefixer: {
                                    flexbox: 'no-2009'
                                },
                                stage: 3
                            }),
                            postcssNormalize()
                        ]
                    }
                }
            },
            {
                loader: 'sass-loader'
            }
        ]
    },
    {
        test: /\.(jpe?g|png|gif)$/,
        use: {
            loader: 'url-loader',
            options: {
                limit: imageInlineSizeLimit,
                name: 'images/[name].[hash:8].[ext]',
            }
        }
    },
    {
        test: /\.js$/,
        exclude: /node_modules/,
        resolve: {
            fullySpecified: false
        },
        use: {
            loader: 'babel-loader'
        }
    },
    {
        test: /\.m?js/,
        resolve: {
          fullySpecified: false
        }
    },
    {
        test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'url-loader',
        options: {
            limit: imageInlineSizeLimit,
            name: 'images/[name].[hash:8].[ext]',
        }
    }
];
