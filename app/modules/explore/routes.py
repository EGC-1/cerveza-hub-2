from flask import jsonify, render_template, request

from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService
from app.modules.dataset.services import CommunityService


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    community_service = CommunityService()
    all_communities = community_service.get_all_communities()
    if request.method == "GET":
        query = request.args.get("query", "")
        form = ExploreForm()
        return render_template("explore/index.html", 
                               form=form, 
                               query=query, 
                               communities=all_communities)

    if request.method == "POST":
        criteria = request.get_json()
        datasets = ExploreService().filter(**criteria)
        return jsonify([dataset.to_dict() for dataset in datasets])
