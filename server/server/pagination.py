from dataclasses import dataclass  # polyfill for Python 3.6 (dataclasses are standard library from Python 3.7)


from flask_restful import reqparse


@dataclass
class PaginationArgs:
    page_number: int
    results_per_page: int


def get_pagination_args() -> PaginationArgs:
    parser = reqparse.RequestParser()
    parser.add_argument('page_number', type=int, required=False, default=1, location='args')
    parser.add_argument('results_per_page', type=int, required=False, default=50, location='args')
    args = parser.parse_args()
    # apply min value
    args['page_number'] = max(args['page_number'], 1)
    args['results_per_page'] = max(args['results_per_page'], 1)
    return PaginationArgs(page_number=args['page_number'], results_per_page=args['results_per_page'])